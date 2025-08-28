""" verify that the user-provided config will execute the generation process
correctly. Should a given argument be invalid, strings are appended to a list
of errors.

Error list to be returned, and used as a basis to feedback to the user that
the configuration as-is is insufficient for successful operation.
"""
from validator.validation_result import ValidationResult


def validate(configurations):
    """ Entry point. Build a list of errors based on a number of tests, when
    returned can be used to feedback to the user what requires changing.

    Parameters
    ----------
    configurations : Configuration
        Configuration object containing all 4 configuration types as specified
        in user and dev configs.

    Returns
    -------
    ValidationResult
        An object containing a boolean flag for success or fail, as well as
        a list of any errors on the case of failure.
    """

    # configurations.get_user_generation_args() and
    # configurations.get_dev_file_builder_args() each return a list of
    # dictionaries, with each dictionary containing a single key/value pair.
    # These are formatted into a single dictionary for validation.

    factory_definitions = {}
    for factory_definition in configurations.get_factory_definitions():
        factory_definitions.update(factory_definition)

    dev_file_builder_args = {}
    for file_builder in configurations.get_dev_file_builder_args():
        dev_file_builder_args.update(file_builder)

    shared_args = configurations.get_shared_args()

    errors = [
        validate_record_counts(factory_definitions),
        validate_max_file_size(factory_definitions),
        validate_google_drive_flag(factory_definitions),
        validate_output_file_extensions(dev_file_builder_args,
                                        factory_definitions),
        validate_pool_sizes_non_zero(shared_args),
        validate_number_of_records_per_job(shared_args, factory_definitions)
    ]

    # Remove instances of None or empty lists from error list
    errors = [error for error in errors if error]
    # Flatten list of lists to single list
    errors = [error for sub_error in errors for error in sub_error]

    # boolean coercion evaluates 'errors' as True if not empty
    if errors:
        return ValidationResult(False, errors)
    else:
        return ValidationResult(True, None)


def validate_record_counts(factory_definitions):
    """ Ensure the record count for each domain object is zero or above.

    Parameters
    ----------
    factory_definitions : dict
        Dictionary of string:dict key/value pairs where keys are names of
        domain objects, and each value is a dictionary containing the
        configuration settings for that domain object.

    Returns
    -------
    List
        List of strings detailing each domain object where record
        count is erroneous. Empty where there are no errors to be found.
    """

    errors = []
    for domain_object, config in factory_definitions.items():
        record_count = config['fixed_args']['record_count']
        if record_count < 0:
            errors.append('- Record count for domain object ' +
                          f'{domain_object} is less than 0')
    return errors


def validate_max_file_size(factory_definitions):
    """ Ensure the maximum file size for each object is greater than 0.

    Parameters
    ----------
    factory_definitions : dict
        Dictionary of string:dict key/value pairs where keys are names of
        domain objects, and each value is a dictionary containing the
        configuration settings for that domain object.

    Returns
    -------
    List
        List of strings detailing each domain object where maximum file
        size is erroneous. Empty where there are no errors to be found.
    """

    errors = []

    for domain_object, config in factory_definitions.items():
        file_size = config['max_objects_per_file']
        if file_size < 0:
            errors.append('- File size for domain object ' +
                          f'{domain_object} is less than 0')
    return errors


def validate_output_file_extensions(dev_file_builder_args,
                                    factory_definitions):
    """ Ensure the file extension for each object is valid as per the defined
    file builders.

    Parameters
    ----------
    dev_file_builder_args : dict
        Dictionary of string:dict key/value pairs where keys are names of
        file builders, and each value is a dictionary containing the
        configuration settings for that file builder.

    factory_definitions : dict
        Dictionary of string:dict key/value pairs where keys are names of
        domain objects, and each value is a dictionary containing the
        configuration settings for that domain object.

    Returns
    -------
    List
        List of strings detailing each domain object where the specified file
        extension
    """

    errors = []
    file_extensions = get_file_extensions(dev_file_builder_args)

    for domain_object, config in factory_definitions.items():
        file_extension = config['output_file_type']
        if file_extension not in file_extensions:
            errors.append(f'- File type \'{file_extension}\' for ' +
                          f'domain object \'{domain_object}\' does not ' +
                          'have a file builder defined')
    return errors


def get_file_extensions(dev_file_builder_args):
    """ Retrieve the file extensions currently supported as per their config
    definitions.

    Parameters
    ----------
    dev_file_builder_args : dict
        Dictionary of string:dict key/value pairs where keys are names of
        file builders, and each value is a dictionary containing the
        configuration settings for that file builder.

    Returns
    -------
    List
        List containing all supported file types.
    """

    return list(dev_file_builder_args.keys())


def validate_pool_sizes_non_zero(shared_args):
    """ Verifies that pool sizes for both generation and writing pools are
    non-zero and positive.

    Parameters
    ----------
    shared_args : dict
        Dictionary of the "shared_config" section of the config file

    Returns
    -------
    List
        Errors where relevant, or empty if none found
    """

    errors = []

    gen_pool_size = shared_args['number_of_create_child_processes']
    write_pool_size = shared_args['number_of_write_child_processes']
    if gen_pool_size <= 0:
        errors.append("- Generation pool size must be a positive value.")
    if write_pool_size <= 0:
        errors.append("- Writing pool size must be a positive value.")
    return errors


def validate_number_of_records_per_job(shared_args, factory_definitions):
    """ Ensure the specified number_of_records_per_job is type int, and if so
    is greater than zero but less than the smallest maximum number of records
    per file

    Parameters
    ----------
    shared_args : dict
        Dictionary of the "shared_config" section of the config file
    factory_definitions : dict
        Dictionary of string:dict key/value pairs where keys are names of
        domain objects, and each value is a dictionary containing the
        configuration settings for that domain object.

    Returns
    -------
    list
        List of a single object, an error message, if job size strictly
        less than zero or greater than the smallest maximum number of records
        per file across all domain objects, contains nothing otherwise.
    """

    errors = []
    number_of_records_per_job = shared_args['number_of_records_per_job']

    if not isinstance(number_of_records_per_job, int):
        errors.append("- 'number_of_records_per_job' must be an integer")

    else:
        try:
            minmax_objects_per_file = min(
                [
                    config['max_objects_per_file']
                    for config in factory_definitions.values()
                    if config['fixed_args']['record_count'] > 0
                ]
            )

            if not 0 < number_of_records_per_job <= minmax_objects_per_file:
                errors.append(
                    "- 'number_of_records_per_job'' must be greater " +
                    "than 0 but not greater than the smallest " +
                    "'max_objects_per_file' value in the config " +
                    "(smallest 'max_objects_per_file': " +
                    f"{minmax_objects_per_file})"
                )

        except ValueError:
            # list comprehension above returned an empty list
            # because all record_count values are 0 or negative
            # which causes min() to throw a ValueError exception
            # the underlying problem will be picked up by the
            # validate_record_counts function, so we need only check that
            # number_of_records_per_job is non-negative
            if not 0 < number_of_records_per_job:
                errors.append(
                    "- 'number_of_records_per_job' must be greater than 0"
                )

    return errors


def validate_google_drive_flag(factory_definitions):
    """ Ensure the google drive flag for each domain object is valid
    (either 'true' or 'false').

    Parameters
    ----------
    factory_definitions : dict
        Dictionary of string:dict key/value pairs where keys are names of
        domain objects, and each value is a dictionary containing the
        configuration settings for that domain object.

    Returns
    -------
    List
        List of strings detailing each domain object where google drive flag
        is erroneous. Empty where there are no errors to be found.
    """
    errors = []
    for domain_object, config in factory_definitions.items():
        google_drive_flag = config['upload_to_google_drive']
        if google_drive_flag.upper() not in ("TRUE", "FALSE"):
            errors.append("- Invalid Google Drive Flag " +
                          f"{google_drive_flag} for domain object " +
                          f"{domain_object}")
    return errors
