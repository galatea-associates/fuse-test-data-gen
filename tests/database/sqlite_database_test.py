import sys

sys.path.insert(0, 'tests/')
from utils import helper_methods as helper
from utils import shared_tests as shared


def test_populate_exchange_table():
    """ Test that the prerequisite table exchanges is properly populated """
    table_name = "exchanges"
    database = helper.create_db()

    database_rows = database.retrieve(table_name)
    rows = []
    for row in database_rows:
        rows.append([row['country_of_issuance'], row['exchange_code'],
                     row['currency']])

    expected_rows = [['US', 'DI', 'USD'], ['GB', 'LN', 'GBP'],
                     ['CA', 'TS', 'CAD'], ['FR', 'GEX', 'EUR'],
                     ['DE', 'FF', 'EUR'], ['CH', 'SWX', 'CHF'],
                     ['SG', 'SG', 'SGD'], ['JP', 'TO', 'JPY']]

    row_count = database.get_table_size(table_name)
    expected_row_count = 8

    shared.actual_contains_expected(expected_rows, rows)
    shared.expected_value(expected_row_count, row_count)


def test_populate_tickers_table():
    """ Test that the prerequisite table tickers is properly populated """
    table_name = "tickers"
    database = helper.create_db()

    rows = database.retrieve_column_as_list(table_name, 'symbol')
    expected_rows = ['YI', 'PIH', 'PIHPP', 'TURN', 'FLWS']

    row_count = database.get_table_size(table_name)
    expected_row_count = 3434

    shared.actual_contains_expected(expected_rows, rows)
    shared.expected_value(expected_row_count, row_count)


def test_persist_batch():
    """ Test that the persist batch method adds records to a given table """

    table_name = "test_instruments"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text"}

    database = helper.create_db()
    helper.create_test_table(database, table_name, table_def)

    instrument1 = ['ric1', 'cusip1', 'TEST_ISIN']
    instrument2 = ['ric2', 'cusip2', 'TEST_ISIN']
    instrument3 = ['ric3', 'cusip3', 'TEST_ISIN']
    instrument_list = [instrument1, instrument2, instrument3]

    database.persist_batch(table_name, instrument_list)
    connection = database.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM " + table_name + " WHERE isin = 'TEST_ISIN'")
    database_rows = cursor.fetchall()

    rows = []
    for row in database_rows:
        rows.append([row['ric'], row['cusip'], row['isin']])

    shared.expected_value(len(instrument_list), len(rows))
    shared.actual_contains_expected(instrument_list, rows)

    helper.drop_test_table(database, table_name)


def test_format_list_for_insertion():
    """ Test that a list for insertion is correctly formatted ready for the
    SQL insert query """

    database = helper.create_db()

    instrument = ['ric', 'cusip', 'TEST_ISIN']
    expecetd_string = "('ric','cusip','TEST_ISIN')"

    formated_string = database.format_list_for_insertion(instrument)
    shared.expected_value(expecetd_string, formated_string)


def test_retrieve():
    """ Test that all records in a table are retrieved when using the
    retrieve method """

    # Setup a test instrument table for tests. Drop and recreate the table at
    # the start of each test

    table_name = "test_instruments"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text"}

    database = helper.create_db()
    helper.create_test_table(database, table_name, table_def)

    instrument1 = ['ric4', 'cusip4', 'TEST_ISIN']
    instrument2 = ['ric5', 'cusip5', 'TEST_ISIN']
    instrument_list = [instrument1, instrument2]

    connection = database.get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric4', 'cusip4', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric5', 'cusip5', "
                                                 "'TEST_ISIN')")

    database_rows = database.retrieve(table_name)
    rows = []
    for row in database_rows:
        rows.append([row['ric'], row['cusip'], row['isin']])

    shared.expected_value(len(instrument_list), len(rows))
    shared.actual_contains_expected(instrument_list, rows)

    helper.drop_test_table(database, table_name)


def test_retrieve_column_as_list():
    """ Test that all records in a specified column in a table are retrieved
    when using the retrieve column as a list method """

    # Setup a test instrument table for tests. Drop and recreate the table at
    # the start of each test

    table_name = "test_instruments"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text"}

    database = helper.create_db()
    helper.create_test_table(database, table_name, table_def)

    ric1 = 'ric4'
    ric2 = 'ric5'
    ric_list = [ric1, ric2]

    connection = database.get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric4', 'cusip4', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric5', 'cusip5', "
                                                 "'TEST_ISIN')")

    rows = database.retrieve_column_as_list(table_name, 'ric')

    shared.expected_value(len(ric_list), len(rows))
    shared.actual_contains_expected(ric_list, rows)

    helper.drop_test_table(database, table_name)


def test_retrieve_batch():
    """ Test that the desired number of records in a table are retrieved when
    using the retrieve batch method """

    # Setup a test instrument table for tests. Drop and recreate the table at
    # the start of each test

    table_name = "test_instruments"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text"}

    database = helper.create_db()
    helper.create_test_table(database, table_name, table_def)

    instrument2 = ['ric2', 'cusip2', 'TEST_ISIN']
    instrument3 = ['ric3', 'cusip3', 'TEST_ISIN']
    instrument4 = ['ric4', 'cusip4', 'TEST_ISIN']

    instrument_list = [instrument2, instrument3, instrument4]

    connection = database.get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric1', 'cusip1', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric2', 'cusip2', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric3', 'cusip3', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric4', 'cusip4', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric5', 'cusip5', "
                                                 "'TEST_ISIN')")

    database_rows = database.retrieve_batch(table_name, 3, 1)
    rows = []
    for row in database_rows:
        rows.append([row['ric'], row['cusip'], row['isin']])

    shared.expected_value(len(instrument_list), len(rows))
    shared.actual_contains_expected(instrument_list, rows)

    helper.drop_test_table(database, table_name)


def test_retrieve_sample():
    """ Test that the desired number of records in a table are retrieved when
    using the retrieve sample method """

    # Setup a test instrument table for tests. Drop and recreate the table at
    # the start of each test

    table_name = "test_instruments"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text"}

    database = helper.create_db()
    helper.create_test_table(database, table_name, table_def)

    connection = database.get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric1', 'cusip1', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric2', 'cusip2', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric3', 'cusip3', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric4', 'cusip4', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric5', 'cusip5', "
                                                 "'TEST_ISIN')")

    sample_size = 3
    database_rows = database.retrieve_sample(table_name, sample_size)
    rows = []
    for row in database_rows:
        rows.append([row['ric'], row['cusip'], row['isin']])

    shared.expected_value(sample_size, len(rows))

    helper.drop_test_table(database, table_name)


def test_table_size():
    """ Test that the get_table_size method returns the true table size """

    # Setup a test instrument table for tests. Drop and recreate the table at
    # the start of each test

    table_name = "test_instruments"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text"}

    database = helper.create_db()
    helper.create_test_table(database, table_name, table_def)

    connection = database.get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric1', 'cusip1', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric2', 'cusip2', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric3', 'cusip3', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric4', 'cusip4', "
                                                 "'TEST_ISIN')")
    cursor.execute("INSERT INTO " + table_name + " (ric, cusip, isin) VALUES ("
                                                 "'ric5', 'cusip5', "
                                                 "'TEST_ISIN')")

    expected_size = 5
    size = database.get_table_size(table_name)

    shared.expected_value(expected_size, size)

    helper.drop_test_table(database, table_name)


def test_drop_table():
    """ Test that a table is dropped if it exists """

    table_name = "test_instruments"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text"}

    database = helper.create_db()
    connection = database.get_connection()
    helper.create_test_table(database, table_name, table_def)

    cursor = connection.cursor()
    cursor.execute("SELECT MAX(CASE WHEN name = '" + table_name + "' "
                   "THEN 1 ELSE 0 END) AS TableExists FROM "
                   "SQLITE_MASTER")

    table_exists = cursor.fetchall()
    exists = []
    for row in table_exists:
        exists.append(row['TableExists'])

    # table exists after creation
    shared.expected_value(1, exists[0])
    shared.expected_value(1, len(exists))

    database.drop_table(table_name)

    cursor = connection.cursor()
    cursor.execute("SELECT MAX(CASE WHEN name = '" + table_name + "' "
                   "THEN 1 ELSE 0 END) AS TableExists FROM "
                   "SQLITE_MASTER")

    table_exists = cursor.fetchall()
    exists = []
    for row in table_exists:
        exists.append(row['TableExists'])

    # table does not exists after deletion
    shared.expected_value(0, exists[0])
    shared.expected_value(1, len(exists))


def test_create_table_from_dict():
    """ Test to check that the table creation method works as expected,
    creating a table as expected with all the desired rows """

    table_name = "test_table"
    table_def = {"ric": "text",
                 "cusip": "text",
                 "isin": "text",
                 "sedol": "text"}

    database = helper.create_db()
    connection = database.get_connection()
    helper.create_test_table(database, table_name, table_def)

    cursor = connection.cursor()
    cursor.execute("SELECT MAX(CASE WHEN name = '" + table_name + "' "
                   "THEN 1 ELSE 0 END) AS TableExists FROM "
                   "SQLITE_MASTER")

    table_exists = cursor.fetchall()
    exists = []
    for row in table_exists:
        exists.append(row['TableExists'])

    cursor.execute("PRAGMA table_info(" + table_name + ")")
    database_rows = cursor.fetchall()
    rows = []
    for row in database_rows:
        rows.append([row['name'], row['type'].lower()])

    # table exists after creation
    shared.expected_value(1, exists[0])
    shared.expected_value(1, len(exists))

    expected_rows = [["ric", "text"], ["cusip", "text"], ["isin", "text"],
                     ["sedol", "text"]]

    # table has the correct rows
    shared.expected_value(expected_rows, rows)
