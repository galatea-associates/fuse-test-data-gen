import random
import string
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta

from database.sqlite_database import Sqlite_Database


class Creatable(ABC):
    """ Parents class of all domain objects. Contains shared creation
    methods, and defines an abstract method for creation. Pre-defines
    lists of potential values for some variations to minimise number of
    list constructions.

    Attributes
    ----------
    LONG_SHORT : List
        Possible values for objects long or short attribute

    ACCOUNT_TYPES : List
        Possible values for objects account_type attribute
        Due to be removed after data model refactor since account type
        will be taken from a persisted Account record

    TRUE_FALSE : List
        Possible values for boolean object attribute

    CURRENCIES : List
        Possible values for objects currency attribute

    ASSET_CLASSES : List
        Possible values for objects asset class attribute

    CREDIT_DEBIT : List
        Possible values for objects credit or debit attribute

    POSITION_TYPES : List
        Possible values for objects position type attribute

    RETURN TYPES : List
        Possible values for objects return type attribute

    config : Dict
        User-specified configuration for domain objects. For shared config and
        domain-specific values, such as swaps per counterparty

    database : SQLite3 Connection
        Connection to the dependency database

    persisting_records : List
        Records, or partial records, to persist to the database. Used to store
        attributes or objects other creations depend on

    Methods
    -------
    create(record_count, start_id) : Abstract
        Create a given number of records, if id'd starting from given number

    create_random_string(length, include_letters, include_numbers)
        Create a random string of letters and/or numbers of given length

    create_random_boolean()
        Select a random boolean value

    create_random_date(from_year, to_year, from_month)
        Creates a random date between a given date and today

    create_random_integer(min, max, length, negative)
        Create a random digit between given values of set length. Boolean
        flag as to positive or negative

    create_random_decimal(min, max, dp)
        Create a random number between two values to a given number of
        decimal places

    create_currency()
        Select a random currency from a pre-defined set

    create_asset_class()
        Select a random asset class from a pre-defined set

    create_ric(ticker, exchange_code)
        Create a RIC value from given ticker and exchange values

    create_isin(country_of_issuance, cusip)
        Create an ISIN value from given county of issuance and CUSIP values

    create_credit_debit()
        Select a random value between credit or debit

    create_long_short()
        Select a random value between long and short

    create_position_type(no_sd, no_td)
        Select a random position type, considering whether there should be
        inclusion of settlement or trade date positions

    create_knowledge_date()
        Return todays date

    create_effective_date(n_days_to_add, knowledge_date, position_type)
        Return today is position is of settlement, else extend by n days

    create_account(account_types)
        Select a random account type from a provided set

    create_return_type()
        Select a random return type from a pre-defined set

    get_random_instrument()
        Return a random instrument from the set of all created intruments

    persist_record(record)
        Add record to list of those to be persisted

    persist_records(table_name)
        Insert list of records to persist to given table

    retrieve_records(table_name)
        Select all records from given table

    retrieve_batch_records(table_name, amount, start_pos)
        Select sequential batch of records from given table starting at pos

    get_database()
        Get connection to the database

    establish_db_connection()
        Connect to database and return connection

    get_object_config()
        Get json configuration of current object

    get_custom_args()
        Get json configuration of current objects custom arguments
    """

    LONG_SHORT = ['Long', 'Short']
    ACCOUNT_TYPES = ['ICP', 'ECP']  # TODO: remove after data model refactor
    TRUE_FALSE = [True, False]
    CURRENCIES = ['USD', 'CAD', 'EUR', 'GBP', 'CHF', 'JPY', 'SGD']
    ASSET_CLASSES = ['Stock', 'Cash']
    CREDIT_DEBIT = ['Credit', 'Debit']
    POSITION_TYPES = ['SD', 'TD']
    RETURN_TYPES = ['Outstanding', 'Pending Return', 'Pending Recall',
                    'Partial Return', 'Partial Recall', 'Settled']

    def __init__(self, factory_args, shared_args):
        """ Set configuration, default database connection to None and
        instantiate list of records to persist to be empty.

        Parameters
        ----------
        factory_args : dict
            Factory settings as set by the user, such as number of records to
            create and any object-specific arguments.
        shared_args : dict
            All multiprocessing arguments and their user-assigned values
        """

        self.__config = factory_args
        self.__shared_args = shared_args
        self.__database = None
        self.__persisting_records = []
        self.instruments = None
        self.accounts = None

    @abstractmethod
    def create(self, record_count, start_id, lock=None):
        """ Create a set number of records for a domain object, where ID's
        are sequential, start from a given id. Concrete implementations
        provided by each domain object """

        pass

    def create_dummy_field_generator(self):
        """ Return generator of dummy fields based on user
        specification in config for the domain object subclass calling
        this function

        Returns
        -------
        Generator:
            iterable that yields key/value pairs as specified in the config
        """
        if self.__config is None:
            # workaround since testing does not always use a config file
            # eventually a testing config will be created and used
            # at which point this 'if' statement can be removed
            return iter(())

        object_name = self.__config["file_type_args"]["xml_item_name"]
        field_number = 1

        for dummy_field in self.__config["dummy_fields"]:
            field_count = dummy_field["field_count"]
            if field_count < 1:
                continue

            data_type = dummy_field["data_type"]
            data_length = dummy_field["data_length"]

            if data_type == "string":
                data_method = self.create_random_string
            elif data_type == "numeric":
                data_method = self.create_random_integer

            for _ in range(field_count):
                yield f'{object_name}_field{field_number}', \
                      data_method(length=data_length)
                field_number += 1

    def create_random_string(self, length,
                             include_letters=True, include_numbers=True):
        """ Creates a random string, of letters or numbers or both.

        Parameters
        ----------
        length : int
            Length of the random string to create
        include_letters : Boolean
            Boolean flag of whether letters are included in the string
        include_numbers : Boolean
            Boolean flag of whether numbers are included in the string

        Returns
        -------
        String
            Random string of letters or numbers or both
        """

        choices = ''
        if include_letters:
            choices += string.ascii_uppercase

        if include_numbers:
            choices += string.digits

        return ''.join(random.choices(choices, k=length))

    def create_random_boolean(self):
        """ Return a random boolean value

        Returns
        -------
        Boolean
            Random True or False value
        """

        return random.choice(self.TRUE_FALSE)

    @staticmethod
    def create_random_date(from_year=2016, from_month=1, from_day=1):
        """ Creates a random date between a 'from_date' and today. if not
        specified, the 'from_date' defaults to 1/1/2016 to ensure a reasonably
        range of dates is available to be selected from.

        Parameters
        ----------
        from_year : int
            Start year for the range
        from_month : int
            Start month for the range
        from_day : int
            Start day for the range

        Returns
        -------
        Date
            Random date between the provided ranges
        """
        from_date = datetime(from_year, from_month, from_day).date()
        today = datetime.now(timezone.utc).date()
        date_range_in_days = (today - from_date).days
        if date_range_in_days < 0:
            raise Exception("from date is in the future")
        return from_date + timedelta(
            days=random.randint(0, date_range_in_days)
        )

    def create_random_integer(self, min=1, max=10000,
                              length=None, negative=False):
        """ Create a random integer of a given length. If no length given,
        create a random integer between minimum and maximum.

        Parameters
        ----------
        min : int
            Minimum value of the range
        max : int
            Maximum value of the range
        length : int
            Length of the integer
        negative : Boolean
            Boolean flag indicating if return value should be negative

        Returns
        -------
        int
            Integer between given min, max values, or of given length, and
            negative if specified.
        """

        if length is not None:
            min = 10 ** (length - 1)
            max = (10 ** length) - 1

        value = random.randint(min, max)
        return value if not negative else -value

    def create_random_decimal(self, min=10, max=10000, dp=2):
        """ Create a random number between a given range to a given number
        of decimal places.

        Parameters
        ----------
        min : int
            Minimum value of the range
        max : int
            Maximum value of the range
        dp : int
            Number of decimal places to create the value to

        Returns
        -------
        float
            Randomly created value between min and max to dp decimal places
        """

        return round(random.uniform(min, max), dp)

    def create_currency(self):
        """ Create a random currency from a set list

        Returns
        -------
        String
            Random currency from a pre-defined list
        """

        return random.choice(self.CURRENCIES)

    def create_asset_class(self):
        """ Create a random asset class from a set list

        Returns
        -------
        String
            Random asset class from a pre-defined list
        """

        return random.choice(self.ASSET_CLASSES)

    def create_ric(self, ticker, exchange_code):
        """ Appends two input values to "ticker.exchange_code"

        Parameters
        ----------
        ticker : String
            a ticker
        exchange_code : String
            an exchange code

        Returns
        -------
        String
            Combined "ticker.exchange_code"
        """

        return '{0}.{1}'.format(ticker, exchange_code)

    def create_isin(self, country_of_issuance, cusip):
        """ Appends two input values to "'country_of_issuance''cusip''4'"

        Parameters
        ----------
        country_of_issuance : String
            a country of issuance code
        cusip : int
            a CUSIP value

        Returns
        -------
        String

        """
        return ''.join([country_of_issuance, str(cusip), '4'])

    def create_credit_debit(self):
        """ Create a random credit or debit value

        Returns
        -------
        String
            Random value between credit or debit
        """

        return random.choice(self.CREDIT_DEBIT)

    def create_long_short(self):
        """ Create a random long or short value

        Returns
        -------
        String
            Random value between long or short
        """

        return random.choice(self.LONG_SHORT)

    def create_position_type(self, no_sd=False, no_td=False):
        """ Create a random position type

        Parameters
        ----------
        no_sd : Boolean
            Boolean flag of whether to include settlement date in choice
        no_td : Boolean
            Boolean flad of whether to include trade date in choice

        Returns
        -------
        String
            Random value between of remaining set of possible position types
        """

        choices = self.POSITION_TYPES
        if no_sd:
            choices.remove('SD')
        if no_td:
            choices.remove('TD')
        return random.choice(choices)

    def create_knowledge_date(self):
        """ Create a knowledge day value

        Returns
        -------
        Date
            Todays date
        """

        return datetime.now(timezone.utc).date()

    def create_effective_date(self, n_days_to_add=3,
                              knowledge_date=None, position_type=None):
        """ Creates an Effective Date value

        Parameters
        ----------
        n_days_to_add : int
            Number of days to add to knowledge date before event takes effect
        knowledge_date : Date
            The knowledge date of the object being created
        position_type : String
            The position type of the object being created

        Returns
        -------
        Date
            Future date if input date was trade date, current date if input
            date was settlement.
        """

        return knowledge_date if position_type == 'SD' \
            else knowledge_date + timedelta(days=n_days_to_add)

    def create_account(self, account_types=ACCOUNT_TYPES):
        """ Creates an account value

        Parameters
        ----------
        account_types : List
            Contains all potential account_types

        Returns
        -------
        String
            Randomly selected account type from list provided/default list
            appended with a 4-digit random string of characters
        """
        # TODO: REMOVE COMPLETELY ONCE ALL FACTORIES UPDATED
        account_type = random.choice(account_types)
        random_string = ''.join(random.choices(string.digits, k=4))
        return ''.join([account_type, random_string])

    def create_return_type(self):
        """ Create a return type

        Returns
        -------
        String
            Random return type chosen from a pre-determined list
        """

        return random.choice(self.RETURN_TYPES)

    # THESE ARE NON-GENERATING, UTILITY METHODS USED WHERE NECESSARY #

    def get_random_record_with_valid_attribute(
            self, table_name, attribute_to_validate, valid_values
    ):
        """ returns a random record from a specified database table, subject
        to the constraint that a specified attribute must have a value in a
        specified list of valid values

        Parameters
        ----------
        table_name : String
            Name of the database table to select the valid record from
        attribute_to_validate: String
            Attribute for which the value will determine if record is valid
        valid_values: List
            List of 1 or more valid values for the attribute given by the
            attribute_to_validate parameter. Only records with values for
            that attribute in this list will be selected in the database
            query.

        Returns
        -------
        SQLite3 Row
            The single row returned by the query
        """

        if self.__database is None:
            self.establish_db_connection()

        return self.__database.retrieve_row_with_valid_attribute(
            table_name, attribute_to_validate, valid_values
        )

    def get_random_instrument(self):
        """ Returns a random instrument from those created prior

        Returns
        -------
        List
            Single record from the instruments table of the database
        """

        if self.instruments is None:
            self.instruments = self.retrieve_records('instruments')
        return random.choice(self.instruments)

    def get_random_account(self):
        """ Returns a random instrument from those created prior

        Returns
        -------
        List
            Single record from the instruments table of the database
        """

        if self.accounts is None:
            self.accounts = self.retrieve_records('accounts')
        return random.choice(self.accounts)

    def get_random_row(self, table_name):
        """ Returns a random from from provided table

                Returns
                -------
                List
                    Single record from the table passed in
                """

        return random.choice(self.retrieve_records(table_name))

    def persist_record(self, record):
        """ Adds a given record to the list of records to persist in storage

        Parameters
        ----------
        record : list
            List of records attributes to store for later insertion
        """

        self.__persisting_records.append(record)

    def persist_records(self, table_name):
        """ Insert all records currently set to be persisted into a specified
        table

        Parameters
        ----------
        table_name : String
            Name of the table to persist records to
        """

        if self.__database is None:
            self.establish_db_connection()
        self.__database.persist_batch(table_name, self.__persisting_records)
        self.__database.commit_changes()

    def retrieve_records(self, table_name):
        """ Selects all records from a given database table

        Parameters
        ----------
        table_name
            Name of the table to retrieve all records of

        Returns
        -------
        SQLite3 Row
            Row object which is iterable, each element contains a Row Object
            the data inwhich can be retrieved as though it's a dictionary
        """

        if self.__database is None:
            self.establish_db_connection()
        return self.__database.retrieve(table_name)

    def retrieve_column(self, table_name, column_name):
        """ Selects one column from a given database table

        Parameters
        ----------
        table_name
            Name of the table to retrieve all records of
        column_name
            Name of the column to be retrieved

        Returns
        -------
        List
            List containing all the values in the specified table and column
        """

        if self.__database is None:
            self.establish_db_connection()
        return self.__database.retrieve_column_as_list(table_name, column_name)

    def retrieve_batch_records(self, table_name, amount, start_pos):
        """ Selects a batch of records from a given table. Retrieval will
        start from the given position, and take the next amount of records

        Parameters
        ----------
        table_name : String
            Name of the table to retrieve from
        amount : int
            Number of records to retrieve in the batch
        start_pos : int
            Position from which to start the retrieval

        Returns
        -------
        SQLite3 Row
            Row object which is iterable, each element contains a Row Object
            the data inwhich can be retrieved as though it's a dictionary
        """

        if self.__database is None:
            self.establish_db_connection()
        return self.__database.retrieve_batch(table_name, amount, start_pos)

    def get_database(self):
        """ Returns the database connection object

        Returns
        -------
        SQLite3 Connection
            Connection to the database
        """

        return self.__database

    def establish_db_connection(self):
        """ Establishes and returns the database connection object

        Returns
        -------
        SQLite3 Connection
            Connection to the database
        """

        self.__database = Sqlite_Database()
        return self.__database

    def get_factory_config(self):
        """ Returns the current objects user-specified configuration

        Returns
        -------
        Dict
            Current objects configuration
        """

        return self.__config

    def get_custom_args(self):
        """ Returns the current objects user-specified custom arguments

        Returns
        -------
        Dict
            Current objects custom arguments
        """

        return self.__config['custom_args']

    def get_shared_args(self):
        """ Returns the shared multiprocessing arguments for multiprocessing.

        Returns
        -------
        Dict
            The arguments shared between factories for multiprocessing.
        """
        return self.__shared_args

    def get_record_count(self):
        """ Returns the number of records the factory is to produce.

        Returns
        -------
        int
            The number of records this factory will produce.
        """
        return int(self.__config['fixed_args']['record_count'])
