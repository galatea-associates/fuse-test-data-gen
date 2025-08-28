from multiprocessing import Manager, Process
from multi_processing.creator import Creator
from multi_processing.writer import Writer
from metrics.metrics_collector import MetricsCollector
import math

# Class to coordinate the multiprocessing implementation. It is
# required to abstract the multiprocessing logic from any unpickleable
# objects, such as the database connection.


class Coordinator:
    """ Coordination class for the multiprocessing implementation. Required
    to abstract multiprocessing calls from unpickleable objects in the main
    program, such as database connections. Holds, instantiates and passes job
    queues to create and write processes, additionally starts these.
    
    Supports comprehensive performance monitoring through MetricsCollector
    integration, capturing timing data for overall pipeline execution,
    batch job counts, and process coordination metrics with minimal overhead.

    Attributes
    ----------
    create_job_queue : Multiprocessing Queue
        Multiprocessing-safe, holds jobs for the create parent process to
        dequeue and run
    created_record_queue : Multiprocessing Queue
        Multiprocessing-safe, holds lists of records created by the create
        parent process for the write parent process to dequeue and write to
        file
    create_coordinator : Creator
        Manages the create parent processes and pool of child processes. Holds
        both 'create_job_queue' and 'created_record_queue' to dequeue jobs
        from the former, and put the created records from those jobs in the
        latter.
    write_coordinator : Writer
        Manages the write  parent processes and pool of child processes.
        Holds the 'created_record_queue', dequeuing batches of jobs from it as
        they arrive and running them over its pool of subprocesses.
    object_factory : Creatable
        Instantiated subclass of Creatable to be used for creating the records
        when running create jobs
    parent_processes : list
        Contains pointers to the create and write parent processes such that
        they can accessed be terminated upon completion.
    metrics_recorder : MetricsCollector
        Optional metrics collection instance for capturing performance data
        including total duration, batch job count, and process coordination timing
...........................................
    Methods
    -------
    populate_create_job_queue()
        Populate the create job queue with jobs based on the number of records
        to generate and the maximum number of records per job as specified in
        the user config

    start_create_parent_process()
        Start the create parent process and append to 'parent_processes'

    start_write_parent_process(pool_size)
        Start the write parent process and append to 'parent_processes'

    start_pipeline_timing()
        Start timing the overall pipeline execution for metrics collection

    join_parent_processes()
        Wait for create & write coordinators to terminate
    """

    def __init__(self, file_builder, object_factory, metrics_recorder=None):
        """Set initial values of instance attributes. Process coordinators will
        not run until their 'parent_process' methods are called.

        Parameters
        ----------
        file_builder : File_Builder
            Instantiated and pre-configured file builder to write files of
            the necessary format.
        object_factory : Creatable
            Instantiated and pre-configured object factory which produces
            the current object.
        metrics_recorder : MetricsCollector, optional
            Metrics collector instance for performance tracking integration.
            Used to capture overall pipeline execution metrics including
            total duration, batch job count, and process coordination timing.
            If None, metrics collection is disabled.
        """

        queue_manager = Manager()
        self.__create_job_queue = queue_manager.Queue()
        self.__created_record_queue = queue_manager.Queue()

        self.__create_coordinator = Creator(
            self.__create_job_queue,
            self.__created_record_queue
        )

        self.__write_coordinator = Writer(
            self.__created_record_queue,
            file_builder.get_max_objects_per_file(),
            file_builder
        )

        self.__object_factory = object_factory
        self.__parent_processes = []
        self.__metrics_recorder = metrics_recorder
        self.__job_count = 0

    def populate_create_job_queue(self):
        """Populate the create job queue with create jobs.

        A create job is a 2-element dictionary. Quantity and Start_ID are
        arguments for an object factory's create call. Quantity informs as to
        the number of objects to produce. Start_ID keeps track of the batch of
        IDs the job will be producing in the case of sequentially ID'd domain
        objects.

        A termination flag is added to the queue last. This informs the
        create parent process to stop awaiting instruction once read, causing
        it to terminate once the currently-running jobs have ceased.
        """

        number_of_records_to_create = self.__object_factory.get_record_count()
        number_of_records_per_job = self.__object_factory.get_shared_args()[
            'number_of_records_per_job'
        ]

        # round up using math.ceil to ensure a job is created for residual
        # records that do not take up a whole file's worth of records

        number_of_create_jobs_to_queue = math.ceil(
            number_of_records_to_create / number_of_records_per_job
        )

        number_of_records_without_create_jobs = number_of_records_to_create
        start_id = 0

        for _ in range(number_of_create_jobs_to_queue):
            quantity = min(
                number_of_records_without_create_jobs,
                number_of_records_per_job
            )

            create_job = {
                'quantity': quantity,
                'start_id': start_id
            }

            self.__create_job_queue.put(create_job)

            start_id += number_of_records_per_job
            number_of_records_without_create_jobs -= quantity

        # Track job count for metrics
        self.__job_count = number_of_create_jobs_to_queue
        
        # Record batch job count in metrics if enabled
        if self.__metrics_recorder:
            self.__metrics_recorder.update_performance_metrics('coordinator', {
                'batch_job_count': self.__job_count,
                'total_records': number_of_records_to_create,
                'records_per_job': number_of_records_per_job
            })

        self.__create_job_queue.put("terminate")

    def start_create_parent_process(self):
        """ Start the create parent process """
        
        # Start overall pipeline timing if this is the first process
        if not self.__parent_processes and self.__metrics_recorder:
            self.start_pipeline_timing()

        create_parent_process = Process(
            target=self.__create_coordinator.parent_process,
            args=(self.__object_factory,)
        )

        create_parent_process.start()

        self.__parent_processes.append(create_parent_process)

    def start_write_parent_process(self):
        """ Starts the write parent process """

        number_of_write_child_processes =\
            self.__object_factory.get_shared_args()[
                'number_of_write_child_processes'
            ]

        write_parent_process = Process(
            target=self.__write_coordinator.parent_process,
            args=(number_of_write_child_processes,)
        )

        write_parent_process.start()

        self.__parent_processes.append(write_parent_process)

    def start_pipeline_timing(self):
        """Start timing the overall pipeline execution for metrics collection.
        
        Records the start time for comprehensive pipeline orchestration timing
        including process startup, coordination, and completion phases.
        """
        if self.__metrics_recorder:
            self.__metrics_recorder.record_start('coordinator_pipeline_execution')
            self.__metrics_recorder.record_start('coordinator_process_coordination')

    def get_metrics_context(self):
        """Get MetricsCollector context manager for pipeline execution timing.
        
        Returns the MetricsCollector instance configured as a context manager
        for automatic metrics lifecycle management during pipeline execution.
        Enables usage with 'with' statements for automatic start/stop timing.
        
        Returns
        -------
        MetricsCollector
            Context manager for automatic metrics collection, or None if 
            metrics recording is disabled
            
        Example
        -------
        >>> with coordinator.get_metrics_context():
        ...     coordinator.populate_create_job_queue()
        ...     coordinator.start_create_parent_process()
        ...     coordinator.start_write_parent_process()
        ...     coordinator.join_parent_processes()
        """
        return self.__metrics_recorder

    def join_parent_processes(self):
        """Waits for spawned child processes to terminate."""
        # Record process coordination end timing
        if self.__metrics_recorder:
            self.__metrics_recorder.record_end('coordinator_process_coordination')
        
        for process in self.__parent_processes:
            process.join()
            
        # Record overall pipeline execution end timing
        if self.__metrics_recorder:
            self.__metrics_recorder.record_end('coordinator_pipeline_execution')
            
            # Update final coordinator performance metrics
            self.__metrics_recorder.update_performance_metrics('coordinator', {
                'processes_managed': len(self.__parent_processes),
                'pipeline_completed': True
            })
