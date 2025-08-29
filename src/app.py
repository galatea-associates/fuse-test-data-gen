""" Random Data Generator for Financial-Domain Objects

    Based on a user provided configuration, generate a set of random data
    pertaining to said configuration. Currently supported domain objects are:

        * Instrument
        * Account
        * Trade
        * Price
        * Front Office Position
        * Back Office Position
        * Depot Position
        * Cash Balance
        * Cash Flow
        * Settlement Instruction

    Domain objects are created sequentially, with one domain object having all
    output files written before starting on the next domain object. This is
    sequenced to ensure that inter-object dependencies are created correctly.

    Dependencies are established using a local SQLite database file. When
    creating a domain object, any fields that may be referenced by dependant
    objects are persisted to the database. Upon creating a dependant object,
    the database is queried to retrieve an appropriate value.

    When creating domain object records and writing them to files,
    multiprocessing is used to increase time efficiency. A Coordinator object
    is responsible for creating and managing these processes, and it will
    spawn two parent processes: 'create_parent_process' and
    'write_parent_process'. These each spawn a number of child processes as
    specified in the 'shared_args' section of the user config.

    See the class docstrings for Writer and Creator for more detail on the
    multiprocessing implementation.

"""

import importlib
import ujson
import os
import sys
from argparse import ArgumentParser
from database.sqlite_database import Sqlite_Database
from multi_processing.coordinator import Coordinator
from exceptions.config_error import ConfigError
from configuration.configuration import Configuration
import validator.config_validator as config_validator
from utils.google_drive_connector import GoogleDriveConnector
from datetime import datetime, timezone
from metrics.metrics_collector import MetricsCollector


def main():
    delete_database()

    configurations = parse_config_files()
    validate_configs(configurations)

    factory_definitions = configurations.get_factory_definitions()
    shared_args = configurations.get_shared_args()
    dev_file_builder_args = configurations.get_dev_file_builder_args()
    dev_factory_args = configurations.get_dev_factory_args()

    current_time_string = datetime.now(timezone.utc).strftime("%H:%M:%S")

    for factory_definition in factory_definitions:
        google_drive_connector = get_google_drive_connector(
            factory_definition,
            current_time_string,
            shared_args)

        file_builder = instantiate_file_builder(factory_definition,
                                                dev_file_builder_args,
                                                google_drive_connector)
        object_factory = instantiate_object_factory(dev_factory_args,
                                                    factory_definition,
                                                    shared_args)
        process_object_factory(file_builder, object_factory)


def process_object_factory(file_builder, object_factory):
    """
    This method is called once per domain object, and instantiates a
    Coordinator object for that domain object. The Coordinator spawns create
    and write processes that use the instantiated object factory and file
    builder respectively to create records and write them to output files.

    Parameters
    ----------
    file_builder : File_Builder
        An instantiated file builder as per this object's required output
        file type specified in the user config
    object_factory : ObjectFactory
        Instantiated subclass of Creatable for the domain object being created.
        Contains creation parameters and multiprocessing shared arguments.
    """

    # Initialize metrics collector for performance monitoring
    metrics_collector = MetricsCollector()
    
    # Get domain object name for metrics tracking
    domain_object_name = type(object_factory).__name__.replace('Factory', '').lower()
    
    # Start timing the overall pipeline execution for this domain object
    pipeline_stage = f"{domain_object_name}_pipeline"
    metrics_collector.record_start(pipeline_stage)

    # Create Coordinator with metrics recorder for performance tracking
    coordinator = Coordinator(file_builder, object_factory, metrics_recorder=metrics_collector)

    # Execute the multiprocessing pipeline
    coordinator.start_create_parent_process()
    coordinator.start_write_parent_process()
    coordinator.populate_create_job_queue()
    coordinator.join_parent_processes()
    
    # End timing for pipeline execution
    metrics_collector.record_end(pipeline_stage)
    
    # Flush metrics to persistent storage
    current_metrics = metrics_collector.get_current_metrics()
    run_id = current_metrics.get('run_id', datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    metrics_collector.flush(run_id)
    
    # Display performance summary to console
    print_performance_summary(current_metrics, domain_object_name)


def instantiate_file_builder(factory_definition,
                             dev_file_builder_args,
                             google_drive_connector):
    """ Returns file builder object from provided configs

    Parameters
    ----------
    factory_definition : dict
        A domain object configuration as specified in the user config
    dev_file_builder_args: dict
        Developer arguments defining where in the codebase file builder
        classes are defined
    google_drive_connector: GoogleDriveConnector
        Connection to enable files created to be uploaded to Google Drive

    Returns
    -------
    FileBuilder
        Instantiated file builder for a single domain object
    """

    factory_args = list(factory_definition.values())[0]

    file_builder_name = factory_args['output_file_type']

    file_builder_config = get_dev_file_builder_config(
        dev_file_builder_args, file_builder_name
    )

    file_builder_class = get_class(
        'filebuilders',
        file_builder_config['module_name'],
        file_builder_config['class_name']
    )

    return file_builder_class(google_drive_connector, factory_args)


def get_google_drive_connector(factory_definition,
                               current_time_string,
                               shared_args):
    """ Return an instance of the Google Drive Connector object if the
    object factory specified in factory_definition is configured to have
    records uploaded to google drive. The Google Drive root folder id specified
    in shared_args is used as the Drive directory for upload.

    If the factory_definition is not configured to upload to Drive, the method
    will return None.

    Parameters
    ----------
    factory_definition : dict
        A domain object configuration as provided by user
    shared_args: dict
        User arguments defining parameters for multiprocessing and google drive
        upload, which are fixed for all object factories and file builders
    current_time_string : string
        Current time in HHMMSS format.  If the files created are uploaded to
        GDrive this will be used as the name of the folder they are uploaded
        into

    Returns
    -------
    GoogleDriveConnector
        Instantiated connector object for uploading to a pre-defined google
        drive directory.
    """
    google_drive_flag = \
        list(factory_definition.values())[0]['upload_to_google_drive'].upper()

    if google_drive_flag == 'TRUE':
        root_folder_id = shared_args['google_drive_root_folder_id']
        return GoogleDriveConnector(root_folder_id, current_time_string)


def instantiate_object_factory(
        dev_factory_args, factory_arguments, shared_args
):
    """ Returns object factory from provided configs

    Parameters
    ----------
    dev_factory_args: dict
        Developer arguments defining where in the codebase factory classes are
        defined
    factory_arguments: dict
        User arguments defining the parameters which generation will adhere to
    shared_args: dict
        User arguments defining parameters for multiprocessing and google drive
        upload, which are fixed for all object factories and file builders

    Returns
    -------
    Creatable
        Instantiated subclass of Creatable for the domain object being
        processed, from the class definition with location in the codebase
        specified in the developer config.

    """

    object_factory_name, factory_args = list(factory_arguments.items())[0]

    object_factory_config = get_dev_object_factory_config(
        dev_factory_args, object_factory_name
    )

    object_factory_class = get_class(
        'domainobjectfactories',
        object_factory_config['module_name'],
        object_factory_config['class_name']
    )

    return object_factory_class(
        factory_arguments[object_factory_name], shared_args
    )


def get_record_count(obj_config, obj_location):
    """ Returns the number of records to be produced for a given object.
    Where objects are non-dependent on others, the user-provided configuration
    amount is used. Otherwise, the record_count is set to be the number of
    records produced of the domain object the to-generate one is dependent
    on.

    Parameters
    ----------
    obj_config : dict
        A domain objects configuration as provided by user
    obj_location : dict
        domain object location configuration from dev config, specifying
        module and class names within the file system

    Returns
    -------
    int
        Number of records to generate, or the number of dependent objects
        generated prior where cur object non-deterministic amount to generate
    """

    nondeterministic_objects = ['swap_contract', 'swap_position', 'cashflow']
    object_module = obj_location['module_name']

    if object_module not in nondeterministic_objects:
        return obj_config['fixed_args']['record_count']
    else:
        db = Sqlite_Database()
        if object_module == 'swap_contract':
            return db.get_table_size('counterparties')
        elif object_module == 'swap_position':
            return db.get_table_size('swap_contracts')
        elif object_module == 'cashflow':
            return db.get_table_size('swap_positions')


def get_dev_file_builder_config(file_builders, file_extension):
    """ Get the configuration of a specified file builder. Iterate over the
    set of file builder keys and if one matches the provided file extension
    then return the full configuration of that file builder.

    Parameters
    ----------
    file_builders : dict
        Parsed json of provided configuration containing parameters for
        all possible filebuilders.
    file_extension: string
        The extension of the file builder configuration which should be
        returned

    Returns
    -------
    dict
        The configuration of the required file builder for the output
        type required.
    """

    file_builder_dict = file_builders[0]
    return file_builder_dict[file_extension]


def get_dev_object_factory_config(dev_factory_args, object_factory_name):
    """ Get the developer-set object configuration specifying where in the
    codebase the class sits.

    Parameters
    ----------
    dev_factory_args : dict
        The locations of all object factories within the codebase
    object_factory_name : string
        The name of the object factory due to be used for generation

    Returns
    -------
    dict
        The module/class names where the given object name sits within the
        codebase
    """

    dev_factory_args_dict = dev_factory_args[0]
    return dev_factory_args_dict[object_factory_name]


def get_class(package_name, module_name, class_name):
    """ Return a given class which sits within a specified heirarchy.
    Used to return classes of filebuilders and domainobjectfactories to only
    instantiate as and when that domainobject/filebuilder is required.

    Parameters
    ----------
    package_name : string
        The package the required class is in
    module_name : string
        The module within the package the required class is in
    class_name : string
        Name of the class

    Returns
    -------
    class
        Uninstantiated requested class
    """
    return getattr(importlib.import_module(package_name + '.' + module_name),
                   class_name)


def parse_config_files():
    """ Retrieve command line arguments, and extract the 4 core configuration
    sections from it. Return this information as a Configuration object.

    Returns
    -------
    Configuration
        An object instantiated to contain all 4 configuration types. Has
        retrieval methods defined within.
    """
    args = get_args()

    with open(args.user_config) as user_config:
        parsed_user_config = ujson.load(user_config)
        factory_definitions = parsed_user_config['factory_definitions']
        shared_args = parsed_user_config['shared_args']

    with open(args.dev_config) as dev_config:
        parsed_dev_config = ujson.load(dev_config)
        dev_file_builder_args = parsed_dev_config['dev_file_builder_args']
        dev_factory_args = parsed_dev_config['dev_factory_args']

    return Configuration(
        {
            "factory_definitions": factory_definitions,
            "shared_args": shared_args,
            "dev_file_builder_args": dev_file_builder_args,
            "dev_factory_args": dev_factory_args
        }
    )


def get_args():
    """ Configure a parser to retrieve & parse command-line arguments
    input by the user.

    Returns
    -------
    namespace
        Namespace is populated with observed arguments, unless none observed,
        in which case default values are returned. Access elements via '.'
        convention, i.e. parser.parse_args().config
    """

    parser = ArgumentParser(description='''Random financial data
                                        generation. For more information,
                                        see the README''')
    parser.add_argument('--user_config', default='src/config.json',
                        help='JSON Configuration File Location')
    parser.add_argument('--dev_config', default='src/dev_config.json',
                        help='Developer Configuration File Location')
    return parser.parse_args()


def validate_configs(configurations):
    """ Ensure that the configuration file found adheres to required format
    to ensure correct generation of domain objects.

    Parameters
    ----------
    configurations : dict
        Parsed json of the user-input configuration

    Excepts
    -------
    ConfigError
        Where an validation of the provided configuration has failed.
        Raised only at the end of all checks such that all errors can be
        reported at once.
    """

    validation_result = config_validator.validate(configurations)

    try:
        if validation_result.check_success():
            print("No errors found in config")
        else:
            raise ConfigError()

    except ConfigError:
        print("Issue(s) within Config:\n")
        for error in validation_result.get_errors():
            print(error)
        sys.exit()


def print_performance_summary(metrics_data, domain_object_name):
    """
    Display performance metrics summary to console after pipeline completion.
    
    Shows key timing information, throughput statistics, and resource utilization
    for the completed data generation pipeline run, providing immediate feedback
    on generation performance.
    
    Parameters
    ----------
    metrics_data : dict
        Complete metrics data structure from MetricsCollector
    domain_object_name : str
        Name of the domain object that was processed
    """
    
    print(f"\n{'=' * 60}")
    print(f"PERFORMANCE SUMMARY - {domain_object_name.upper()}")
    print(f"{'=' * 60}")
    
    # Display run identification
    run_id = metrics_data.get('run_id', 'Unknown')
    print(f"Run ID: {run_id}")
    
    # Display timing information
    total_duration = metrics_data.get('total_duration_seconds')
    if total_duration is not None:
        print(f"Total Duration: {total_duration:.2f} seconds")
        print(f"Start Time: {metrics_data.get('start_time', 'Unknown')}")
        print(f"End Time: {metrics_data.get('end_time', 'Unknown')}")
    
    # Display stage timings if available
    stage_timings = metrics_data.get('stage_timings', {})
    if stage_timings:
        print(f"\nStage Timings:")
        for stage_name, stage_data in stage_timings.items():
            duration = stage_data.get('duration_seconds', 0)
            print(f"  {stage_name}: {duration:.2f} seconds")
    
    # Display throughput metrics if available
    throughput_data = metrics_data.get('performance', {}).get('throughput', {})
    if throughput_data:
        print(f"\nThroughput Metrics:")
        total_records = throughput_data.get('total_records_processed', 0)
        current_rate = throughput_data.get('current_records_per_second', 0)
        peak_rate = throughput_data.get('peak_records_per_second', 0)
        
        print(f"  Total Records Processed: {total_records:,}")
        if current_rate > 0:
            print(f"  Average Rate: {current_rate:.0f} records/second")
        if peak_rate > 0:
            print(f"  Peak Rate: {peak_rate:.0f} records/second")
    
    # Display resource utilization if available
    resource_util = metrics_data.get('resource_utilization', {})
    if resource_util:
        print(f"\nResource Utilization:")
        peak_memory = resource_util.get('peak_memory_mb')
        avg_cpu = resource_util.get('avg_cpu_percent')
        process_count = resource_util.get('process_count')
        
        if peak_memory is not None:
            print(f"  Peak Memory Usage: {peak_memory:.1f} MB")
        if avg_cpu is not None:
            print(f"  Average CPU Usage: {avg_cpu:.1f}%")
        if process_count is not None:
            print(f"  Process Count: {process_count}")
    
    # Display configuration information if available
    config_data = metrics_data.get('configuration', {})
    if config_data:
        record_counts = config_data.get('record_counts', {})
        if record_counts:
            print(f"\nGeneration Configuration:")
            for factory_name, count in record_counts.items():
                print(f"  {factory_name}: {count:,} records")
    
    # Display error summary if there were any issues
    error_summary = metrics_data.get('error_summary', {})
    total_errors = error_summary.get('total_errors', 0)
    warnings = error_summary.get('warnings', 0)
    
    if total_errors > 0 or warnings > 0:
        print(f"\nIssues Summary:")
        if total_errors > 0:
            print(f"  Errors: {total_errors}")
        if warnings > 0:
            print(f"  Warnings: {warnings}")
        
        last_error = error_summary.get('last_error')
        if last_error:
            print(f"  Last Issue: {last_error}")
    
    print(f"{'=' * 60}")
    print(f"Metrics saved to: metrics/runs/{run_id}.json")
    print(f"{'=' * 60}\n")


def delete_database():
    """ Remove an existing database if one already exists. Used to ensure
    that subsequent generation is from a valid set of pre-generated
    dependencies.
    """

    if os.path.exists('dependencies.db'):
        os.unlink('dependencies.db')


if __name__ == '__main__':
    main()
