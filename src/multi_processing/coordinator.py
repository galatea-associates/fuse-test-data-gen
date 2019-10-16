from multiprocessing import Manager, Process
from multi_processing.generator import Generator
from multi_processing.writer import Writer

# Class to coordinate the multiprocessing implementation. It is
# required to abstract the multiprocessing logic from any unpickleable
# objects, such as the database connection.


class Coordinator():
    """ Coordination class for the multiprocessing implementation. Required
    to abstract multiprocessing calls from unpickleable objects in the main
    program, such as database connections. Holds, instantiates and passes job
    queues to generation and writing processes, additionally starts these.

    Attributes
    ----------
    generation_job_queue : Multiprocessing Queue
        Multiprocessing-safe, holds jobs for the generation process to format
        and execute.
    write_job_queue : Multiprocessing Queue
        Multiprocessing-safe, holds jobs for the writing process to format and
        execute.
    generation_coordinator : Generator
        Holds both queues to take jobs from the former, and put the results of
        such in the latter.
    write_coordinator : Writer
        Holds writing job queue, taking jobs from which and formatting them
        before writing files of the user-given size.
    processes : list
        Adds started processes (Generator and Writer) for the purpose of
        knowing once they're finished.

    Methods
    -------
    create_jobs(domain_obj, quantity, job_size)
        Populate the generation job queue with jobs

    start_generator(obj_class, pool_size)
        Begin the generation coordinator as a subprocess, with job pool size

    start_writer(pool_size)
        Begin the writing coordinator as a subprocess, with job pool size

    get_generation_coordinator()
        Return the generation coordinator

    get_write_coordinator()
        Return the write coordinator

    await_termination()
        Wait for generation & write coordinators to terminate
    """

    def __init__(self, max_file_size, file_builder):
        """Create Job Queues for both generation and writing to file, as well
        as instantiating the coordinators for both.

        Parameters
        ----------
        max_file_size : int
            The maximum number of records to write to each file
        file_builder : File_Builder
            Instantiated and pre-configured file builder to write files of
            the necessary format.
        """

        queue_manager = Manager()
        self.__generation_job_queue = queue_manager.Queue()
        self.__write_job_queue = queue_manager.Queue()

        self.__generation_coordinator = Generator(
            self.__generation_job_queue,
            self.__write_job_queue
        )

        self.__write_coordinator = Writer(
            self.__write_job_queue,
            max_file_size,
            file_builder
        )

        self.processes = []

    def create_jobs(self, domain_obj, quantity, job_size):
        """Populate the generation queue with jobs.

        Continually places jobs into the queue, counting down quantity until
        it's value is 0. Where quantity larger than job size, a job is spawned
        of job size, and quantity decremented that amount. Where quantity less
        than job size, a job is spawned of size quantity.

        A job is a 3-element dictionary. Domain object name provided for the
        purpose of keeping track. Amount and Start_ID are arguments for the
        generate call. Amount informs as to the number of records to generate.
        Start_ID keeps track of the batch of IDs the job will be generating
        in the case of sequentially ID'd domain objects.

        Finally, a termination flag is added to the queue. This informs the
        coordinator to stop awaiting instruction once read, causing it to
        terminate once the currently-running jobs have ceased.

        Parameters
        ----------
        domain_obj : Generatable
            Domain object name to be generated
        quantity : int
            Number of records to be generated for domain_obj
        job_size : int
            Number of records to be generated by each generating process
        """
        start_id = 0
        record_count = int(quantity)

        while record_count > 0:
            if record_count > job_size:
                job = {'domain_object': domain_obj,
                       'amount': job_size,
                       'start_id': start_id}
                record_count = record_count - job_size
                start_id = start_id + job_size
            else:
                job = {'domain_object': domain_obj,
                       'amount': record_count,
                       'start_id': start_id}
                record_count = 0
            self.__generation_job_queue.put(job)

        self.__generation_job_queue.put("terminate")

    def start_generator(self, obj_class, pool_size):
        """ Starts the generation coordinator as a subprocess

        Parameters
        ----------
        obj_class : String
            For keeping track of which domain object is being generated
        pool_size : int
            The number of processes running in the generator's pool
        """

        generator_p = Process(target=self.get_generation_coordinator().start,
                              args=(obj_class, pool_size,))
        generator_p.start()
        self.processes.append(generator_p)

    def start_writer(self, pool_size):
        """ Starts the writing coordinator as a subprocess

        Parameters
        ----------
        pool_size : int
            The number of processes running in the writer's pool
        """

        writer_p = Process(target=self.get_write_coordinator().start,
                           args=(pool_size,))
        writer_p.start()
        self.processes.append(writer_p)

    def get_generation_coordinator(self):
        """
        Returns
        -------
        Generator
            Instantiated Generator class, handles generation of domain objects
        """

        return self.__generation_coordinator

    def get_write_coordinator(self):
        """
        Returns
        -------
        Writer
            Instantiated Writer class, handles writing of domain objects to
            file
        """

        return self.__write_coordinator

    def await_termination(self):
        """Waits for spawned subprocesses to terminate."""
        for process in self.processes:
            process.join()
