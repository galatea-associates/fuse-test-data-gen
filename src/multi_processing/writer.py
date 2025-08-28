import time
from multi_processing import pool_tasks
from metrics.metrics_collector import MetricsCollector


class Writer:
    """ A class to coordinate the writing of created records by
    compiling pre-generated records from a Multiprocessed Queue into larger
    sets such that files can be written in user-requested sizes.

    The write parent process waits until the 'generated_record_queue' is not
    empty, at which point it retrieves lists of records from the queue and
    collates all records from those lists into a
    'dequeued_created_records_not_yet_written_to_file' list.

    It then creates a list of 'write jobs', each of which is a dictionary
    containing a portion of the records from the
    'dequeued_created_records_not_yet_written_to_file' list to write to file,
    and the ID of the output file. A single output file can have multiple
    'write jobs', but a 'write job' can only refer to one output file.

    The 'write jobs' in the list are run over a pool of child write processes,
    which build the output files then terminate. Upon termination of all
    processes, the 'write job' list is emptied and the next iteration begins by
    dequeuing any further records from the 'generated_record_queue'.

    Attributes
    ----------
    created_record_queue : Multiprocessed Queue
        Contains results of the generation process. Each element is a list of
        lists of records.
    dequeued_created_records_not_yet_written_to_file : list
        list collating all records dequeued from the created record queue that
        have not yet been written to file
    number_of_next_file_to_write : int
        The current file number to be writing to.
    max_records_per_file : int
        The maximum number of records in each output file.
    write_jobs : list
        List of jobs to be run
    terminate_dequeued : boolean
        Boolean flag which when True indicates the coordinator is to terminate
    file_builder : FileBuilder
        Instantiated file builder, pre-configured to output the necessary file
        extension.

    Methods
    -------
    parent_process()
        Begin the cycle of waiting for, handling and running jobs. Continue
        this until termination instruction observed
    sleep_while_created_record_queue_empty()
        Sleeps until items are observed on the Multiprocessed Queue.
    create_write_jobs()
        Takes items from the created records queue and adds write jobs to
        the write jobs list representing these records. If a terminate
        instruction is dequeued, the appropriate flag is set.
    get_write_job()
        Create a single write job representing the records at the front of
        the 'dequeued_created_records_not_yet_written_to_file' list. Delete
        these records from the list, then return the write job.
    """

    def __init__(
            self, created_record_queue, max_records_per_file, file_builder
    ):
        """ Initialise instance attributes.

        Parameters
        ----------
        created_record_queue : Multiprocessing Queue
            Shared, multiprocessing safe, queue holding lists of lists of
            records
        max_records_per_file : int
            Value representing the maximum number of records per file
        file_builder : File_Builder
            Instantiated file builder, pre-configured to output the necessary
            file extension.
        """

        self.created_record_queue = created_record_queue
        self.dequeued_created_records_not_yet_written_to_file = []
        self.number_of_next_file_to_write = 0
        self.max_records_per_file = max_records_per_file
        self.write_jobs = []
        self.terminate_dequeued = False
        self.file_builder = file_builder

    def parent_process(self, number_of_write_child_processes):
        """ Begin the cycle of waiting for, handling, and running jobs,
        continuing this until an instruction to terminate is observed. Once
        observed, calculate any residual write to be made and terminate.

        Parameters
        ----------
        number_of_write_child_processes : int
            The number of processes running in the generator's pool
        """
        # Initialize metrics collector with context manager for comprehensive performance tracking
        metrics_collector = MetricsCollector()
        
        with metrics_collector:
            # Track overall writer parent process execution time
            metrics_collector.record_start('writer_parent_process')
            
            # Initialize performance tracking variables
            total_files_written = 0
            total_records_processed = 0
            total_batches_processed = 0
            
            try:
                maximum_number_of_write_jobs_to_create = \
                    2 * number_of_write_child_processes

                while not self.terminate_dequeued:
                    # Time queue polling operations for performance analysis
                    metrics_collector.record_start('writer_queue_polling')
                    self.sleep_while_created_record_queue_empty()
                    metrics_collector.record_end('writer_queue_polling')
                    
                    # Time record buffering and write job creation
                    metrics_collector.record_start('writer_record_buffering')
                    initial_job_count = len(self.write_jobs)
                    records_before_buffering = len(self.dequeued_created_records_not_yet_written_to_file)
                    
                    self.create_write_jobs(
                        maximum_number_of_write_jobs_to_create
                    )
                    
                    records_after_buffering = len(self.dequeued_created_records_not_yet_written_to_file)
                    jobs_created_this_iteration = len(self.write_jobs) - initial_job_count
                    metrics_collector.record_end('writer_record_buffering')
                    
                    if self.write_jobs:
                        # Time file writing operations with detailed performance tracking
                        metrics_collector.record_start('writer_file_operations')
                        batch_start_time = time.perf_counter()
                        
                        # Track batch size and record counts for this write operation
                        current_batch_size = len(self.write_jobs)
                        records_in_current_batch = sum(len(job.get('records', [])) for job in self.write_jobs)
                        
                        pool_tasks.run_write_jobs(
                            self.write_jobs,
                            number_of_write_child_processes,
                            self.file_builder
                        )
                        
                        batch_end_time = time.perf_counter()
                        batch_duration = batch_end_time - batch_start_time
                        metrics_collector.record_end('writer_file_operations')
                        
                        # Update performance counters and calculate throughput metrics
                        total_files_written += current_batch_size
                        total_records_processed += records_in_current_batch
                        total_batches_processed += 1
                        
                        # Calculate and record write performance metrics
                        if batch_duration > 0:
                            files_per_second = current_batch_size / batch_duration
                            records_per_second = records_in_current_batch / batch_duration
                            
                            # Update performance metrics in collector
                            performance_metrics = {
                                'batch_files_per_second': files_per_second,
                                'batch_records_per_second': records_per_second,
                                'batch_duration_seconds': batch_duration,
                                'batch_size_files': current_batch_size,
                                'batch_size_records': records_in_current_batch,
                                'avg_records_per_file': records_in_current_batch / current_batch_size if current_batch_size > 0 else 0,
                                'total_files_written': total_files_written,
                                'total_records_processed': total_records_processed,
                                'total_batches_processed': total_batches_processed
                            }
                            metrics_collector.update_performance_metrics('writers', performance_metrics)
                            
                            # Record throughput for overall system tracking
                            metrics_collector.record_throughput(records_in_current_batch, batch_duration)
                        
                        self.write_jobs = []

                # Handle residual records with metrics tracking
                if self.dequeued_created_records_not_yet_written_to_file:
                    # list is not empty - there are some residual records remaining
                    metrics_collector.record_start('writer_residual_processing')
                    residual_start_time = time.perf_counter()
                    
                    residual_job = self.get_write_job()
                    residual_record_count = len(residual_job.get('records', []))
                    
                    pool_tasks.run_write_jobs(
                        [residual_job],
                        number_of_write_child_processes,
                        self.file_builder
                    )
                    
                    residual_end_time = time.perf_counter()
                    residual_duration = residual_end_time - residual_start_time
                    metrics_collector.record_end('writer_residual_processing')
                    
                    # Update final performance metrics including residual processing
                    total_files_written += 1
                    total_records_processed += residual_record_count
                    
                    if residual_duration > 0:
                        residual_performance = {
                            'residual_processing_duration': residual_duration,
                            'residual_record_count': residual_record_count,
                            'residual_records_per_second': residual_record_count / residual_duration,
                            'final_total_files_written': total_files_written,
                            'final_total_records_processed': total_records_processed
                        }
                        metrics_collector.update_performance_metrics('writers', residual_performance)
                
                # Record final writer performance summary
                metrics_collector.record_end('writer_parent_process')
                
                # Calculate overall writer process resource utilization and efficiency
                final_metrics = {
                    'total_write_cycles': total_batches_processed,
                    'avg_files_per_batch': total_files_written / total_batches_processed if total_batches_processed > 0 else 0,
                    'avg_records_per_batch': total_records_processed / total_batches_processed if total_batches_processed > 0 else 0,
                    'child_processes_utilized': number_of_write_child_processes,
                    'max_jobs_per_iteration': maximum_number_of_write_jobs_to_create
                }
                metrics_collector.update_performance_metrics('writers', final_metrics)
                
            except Exception as e:
                # Ensure metrics are captured even if an exception occurs
                metrics_collector.record_end('writer_parent_process')
                # Record the error but re-raise to maintain original behavior
                error_metrics = {
                    'writer_error': str(e),
                    'files_written_before_error': total_files_written,
                    'records_processed_before_error': total_records_processed
                }
                metrics_collector.update_performance_metrics('writers', error_metrics)
                raise
            
            # Flush metrics to ensure all performance data is persisted
            # The context manager will handle the final flush, but this ensures
            # all writer-specific metrics are properly recorded
            metrics_collector.flush(metrics_collector._run_id or 'writer_process')

    def sleep_while_created_record_queue_empty(self):
        """ Sleep until records are on the queue """

        while self.created_record_queue.empty():
            time.sleep(1)
        return

    def create_write_jobs(self, maximum_number_of_write_jobs_to_create):
        """ Takes items from the created records queue and adds write jobs to
        the write jobs list representing these records. If a terminate
        instruction is dequeued, the appropriate flag is set.

        Parameters
        ----------
        maximum_number_of_write_jobs_to_create : int
            The maximum number of write jobs to add to self.write_jobs
        """

        while not self.created_record_queue.empty() and \
                len(self.write_jobs) < maximum_number_of_write_jobs_to_create:

            dequeued_created_records = self.created_record_queue.get()

            if dequeued_created_records == "terminate":
                self.terminate_dequeued = True
            else:
                self.dequeued_created_records_not_yet_written_to_file.extend(
                    dequeued_created_records
                )
                while len(
                        self.dequeued_created_records_not_yet_written_to_file
                ) >= self.max_records_per_file:
                    self.write_jobs.append(self.get_write_job())

    def get_write_job(self):
        """ Create a single write job representing the records at the front of
        the 'dequeued_created_records_not_yet_written_to_file' list. Delete
        these records from the list, then return the write job.
        """

        number_of_records = min(
            self.max_records_per_file, len(
                self.dequeued_created_records_not_yet_written_to_file
            )
        )

        write_job = {
            'file_number': self.number_of_next_file_to_write,
            'records': self.dequeued_created_records_not_yet_written_to_file[
                       :number_of_records
                       ]
        }

        self.number_of_next_file_to_write += 1

        del self.dequeued_created_records_not_yet_written_to_file[
            :number_of_records
            ]

        return write_job
