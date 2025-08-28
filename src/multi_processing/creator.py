import time
from multi_processing import pool_tasks
from metrics.metrics_collector import MetricsCollector


class Creator:
    """ A class to coordinate the creation of domain objects as specified by
    'create jobs' from the multiprocessing-safe queue 'create_job_queue'.
    'Create jobs' are sequentially dequeued in batches and run over a pool of
    child processes, returning a list containing all created records from the
    jobs in that batch.

    A 'create job' is a dictionary specifying a quantity of domain object
    records to be created and later written to output file. The maximum
    quantity of records in a 'create job' is specified in the 'shared_args'
    section of the user config by the 'number_of_records_per_job' key.

    The create parent process will wait until the 'create_job_queue' is not
    empty, at which point it will dequeue 'create jobs' and add them to a list.
    It will not dequeue more than double the number of child create processes
    worth of create jobs at a time to ensure that the child processes work on
    reasonable sized batches of create jobs.

    The dequeued 'create jobs' in the list are executed over a pool of child
    create processes which, upon termination of all child processes, returns
    a list of created records. This list contains the collated output from that
    batch of 'create jobs'.

    As batches of 'create jobs' are run, the returned lists of records are
    added to a FIFO 'generated_record_queue'. This queue is shared between the
    create and write parent processes.

    Attributes
    ----------
    create_job_queue : Multiprocess Queue
        Multiprocess safe queue from which jobs to create records are taken
    created_record_queue : Multiprocess Queue
        Multiprocess safe queue into which lists of created records are placed
    terminate_dequeued : Boolean
        Boolean flag which when True indicates the coordinator is to terminate

    Methods
    -------
    parent_process(object_factory)
        Until the "terminate" flag is dequeued, cycle through a loop that waits
        until the create job queue is not empty, then dequeues and runs a batch
        of jobs, and puts a list of created records from that batch onto the
        created record queue.
    sleep_while_create_job_queue_empty()
        Sleep whilst the create job queue is empty
    get_dequeued_create_jobs(maximum_number_of_create_jobs_to_dequeue)
        Return a list containing a batch of jobs dequeued from the create job
        queue such that they can be run over a pool of child processes
    """

    def __init__(self, create_job_queue, created_record_queue):
        """ Assign variables from input, and set termination to False

        Parameters
        ----------
        create_job_queue : Multiprocessed Queue
            Queue containing jobs to create a certain quantity of domain
            objects
        created_record_queue : Multiprocessed Queue
            Queue containing lists of records creating from running
            'create jobs'
        """

        self.create_job_queue = create_job_queue
        self.created_record_queue = created_record_queue
        self.terminate_dequeued = False

    def parent_process(self, object_factory):
        """ Begin the cycle of waiting for, formatting, and running jobs,
        continuing this until an instruction to terminate is observed.

        Parameters
        ----------
        object_factory : Creatable
            Instantiated and pre-configured object factory used to create
            records from create jobs
        """

        # Initialize metrics collector for performance monitoring
        metrics_collector = MetricsCollector()
        
        # Use metrics collector as context manager for comprehensive timing
        with metrics_collector:
            metrics_collector.record_start('creator_parent_process_total')

            number_of_create_child_processes =\
                object_factory.get_shared_args()[
                    'number_of_create_child_processes'
                ]

            # the maximum number of jobs to dequeue for processing is proportional
            # to the number of processes available to execute the jobs

            maximum_number_of_create_jobs_to_dequeue = \
                number_of_create_child_processes * 2

            batch_count = 0
            total_records_processed = 0

            while not self.terminate_dequeued:
                # Time the queue polling/waiting phase
                metrics_collector.record_start('creator_queue_wait')
                self.sleep_while_create_job_queue_empty()
                metrics_collector.record_end('creator_queue_wait')

                # Time the job dequeuing phase  
                metrics_collector.record_start('creator_job_dequeue')
                dequeued_create_jobs = self.get_dequeued_create_jobs(
                    maximum_number_of_create_jobs_to_dequeue
                )
                metrics_collector.record_end('creator_job_dequeue')

                if dequeued_create_jobs:  # Only process if we have jobs
                    batch_count += 1
                    
                    # Calculate batch size for throughput metrics
                    batch_record_count = sum(
                        job.get('quantity_to_create', 0) 
                        for job in dequeued_create_jobs 
                        if isinstance(job, dict)
                    )
                    
                    # Time the record creation processing phase
                    metrics_collector.record_start('creator_record_creation')
                    batch_start_time = time.perf_counter()
                    
                    created_records_from_multiple_jobs = \
                        pool_tasks.run_create_jobs(
                            dequeued_create_jobs,
                            number_of_create_child_processes,
                            object_factory
                        )
                    
                    batch_end_time = time.perf_counter()
                    batch_duration = batch_end_time - batch_start_time
                    metrics_collector.record_end('creator_record_creation')
                    
                    # Calculate actual record count from created records
                    actual_record_count = len(created_records_from_multiple_jobs) if created_records_from_multiple_jobs else 0
                    total_records_processed += actual_record_count
                    
                    # Record throughput metrics for this batch
                    if batch_duration > 0:
                        metrics_collector.record_throughput(actual_record_count, batch_duration)
                    
                    # Time the queue put operation
                    metrics_collector.record_start('creator_queue_put')
                    self.created_record_queue.put(created_records_from_multiple_jobs)
                    metrics_collector.record_end('creator_queue_put')

            # Record final termination queue put
            metrics_collector.record_start('creator_termination_put')
            self.created_record_queue.put("terminate")
            metrics_collector.record_end('creator_termination_put')
            
            # Record final performance metrics for the creator component
            metrics_collector.record_end('creator_parent_process_total')
            
            # Update performance metrics with final statistics
            creator_metrics = {
                'total_batches_processed': batch_count,
                'total_records_created': total_records_processed,
                'avg_records_per_batch': total_records_processed / batch_count if batch_count > 0 else 0,
                'number_of_child_processes': number_of_create_child_processes
            }
            metrics_collector.update_performance_metrics('creators', creator_metrics)

    def sleep_while_create_job_queue_empty(self):
        """ Sleep until jobs are on the queue """

        while self.create_job_queue.empty():
            time.sleep(1)

    def get_dequeued_create_jobs(
            self, maximum_number_of_create_jobs_to_dequeue
    ):
        """ Dequeues 'create jobs' from the Multiprocess Safe Queue
        'create_job_queue' and places them into a list for later execution.

        If twice the number of create child processes are dequeued, then the
        list is returned - this is to ensure the pool of child processes will
        not run over an inefficiently large batch of 'create jobs'.

        If the termination flag is observed, then this list is returned.

        If the queue becomes empty, then the list so far is returned.

        Parameters
        ----------
        object_factory : Creatable
            Instantiated and pre-configured object factory which produces
            the current object.
        maximum_number_of_create_jobs_to_dequeue : int
            the maximum number of jobs to dequeue for processing

        Returns
        -------
        List
            Containing jobs taken from the Queue. A list intermediary is
            required as multiprocessing pools require an iterable object,
            which a multiprocessing queue is not.
        """

        dequeued_create_jobs = []

        while not self.create_job_queue.empty() and len(dequeued_create_jobs) \
                < maximum_number_of_create_jobs_to_dequeue:

            create_job = self.create_job_queue.get()

            if create_job == "terminate":
                self.terminate_dequeued = True
            else:
                dequeued_create_jobs.append(create_job)

        return dequeued_create_jobs
