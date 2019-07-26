from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import random
import string

class Generatable(ABC):   

    def __init__(self, cache): 
        self.cache = cache

    @abstractmethod
    def generate(self, record_count, custom_args):
       pass
      
    def generate_random_string(self, length):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
     
    def generate_random_boolean(self):
        return random.choice([True, False])
    
    def generate_random_date(self, from_year=2016, to_year=2017,
                                 from_month=1, to_month=12,
                                 from_day=1, to_day=28):
        year = random.randint(from_year, to_year)
        month = random.randint(from_month, to_month)
        day = random.randint(from_day, to_day)
        return datetime(year, month, day).date()
    
    def generate_random_integer(self, min=1, max=10000, length=None):        
        if length is not None:
            min = 10**(length-1)
            max = (10**length)-1

        return random.randint(min,max) 
    
    def generate_random_decimal(self, min=10, max=10000, dp=2):          
        return round(random.uniform(min, max), dp)

    def generate_currency(self):
        return random.choice(['USD', 'CAD', 'EUR', 'GBP'])
    
    def generate_asset_class(self):
        return random.choice(['Stock', 'Cash'])
    
    def generate_ric(self, ticker, exchange_code):
        return '{0}.{1}'.format(ticker, exchange_code)
    
    def generate_isin(self, coi, cusip):
        return coi + cusip + '4'
    
    def generate_credit_debit(self):
        return random.choice(['Credit', 'Debit'])
    
    def generate_long_short(self):
        return random.choice(['Long', 'Short'])
    
    def generate_position_type(self, no_sd=False, no_td=False):
        choices = ['SD', 'TD']
        if no_sd:
            choices.remove('SD')
        if no_td:
            choices.remove('TD')
        return random.choice(choices)
    
    def generate_knowledge_date(self):
        return datetime.today()
    
    def generate_effective_date(self, n_days_to_add=3, knowledge_date=None, position_type=None):
        return knowledge_date if position_type == 'SD' else knowledge_date + timedelta(days=n_days_to_add)

    def generate_account(self, account_types=['ICP, ECP']):
        account_type = random.choice(account_types)
        return account_type + ''.join([random.choice(string.digits) for _ in range(4)])      
       
    def generate_return_type(self):
        return random.choice(['Outstanding', 'Pending Return', 'Pending Recall',
                              'Partial Return', 'Partial Recall', 'Settled'])
     
    def generate_ticker(self):
        return random.choice(self.cache.retrieve_from_cache('tickers'))

    def generate_coi(self):
        return random.choice(self.cache.retrieve_from_cache('cois'))

    def generate_exchange_country(self):
        return random.choice(self.cache.retrieve_from_cache('exchanges_countries'))            