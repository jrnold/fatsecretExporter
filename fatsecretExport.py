#!/usr/bin/env python2.6
"""
This is quick and dirty script to export the fatsecret food, exercise,
and weight entries to csv files. I wrote it to get my data from fatsecret for analysis.

I don't have the time to write a web app or host one; so if you want
to use this, you need to get your own developer API key from fatsecret.

This depends on the python fatsecret (http://bitbucket.org/fmoo/python-fatsecret/)
bindings to the fatsecret REST api.

To use, you need to place a configuration file in the location
specified by the CONFIG variable below (usually ~/.fatsecret).
The configuration file should have the following keys defined:

{{{
[consumer]
   key:adkfasjdfasdafds
   secret:sdjfaksfblasfs
[user]
   name:fatsecret_username
   datastore:/home/foo/fatsecret_tokens.dat
}}}

"""

import ConfigParser
from optparse import OptionParser
import csv
import os.path
import sys
import time
from oauth import oauth
from datetime import date, timedelta
from fatsecret import FatSecretClient, TokenShelf

CONFIG = os.path.expanduser("~/.fatsecret")

## Date that fatsecret uses as its epoch
FSEpoch = date(1970, 1, 1)

# Override the FatSecretApplication class in python-fatsecret
# so that I can get a working __init__ function
class FatSecretApplication(oauth.OAuthConsumer):
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

class NewFatSecretClient(FatSecretClient):
    ## amount of time to delay between API calls
    delay = 1
    
    def get_food(self, startdate, enddate):
        fields = ['date',
                  'food_entry_id',
                  'food_entry_description',
                  'meal',
                  'food_id',
                  'serving_id',
                  'number_of_units',
                  'food_entry_name',
                  'calories',
                  'carbohydrate',
                  'protein',
                  'fat',
                  'saturated_fat',
                  'polyunsaturated_fat',
                  'monounsaturated_fat',
                  'trans_fat',
                  'cholesterol',
                  'sodium',
                  'potassium',
                  'fiber',
                  'sugar',
                  'vitamin_a',
                  'vitamin_c',
                  'calcium',
                  'iron']

        food_entries = [] 
        d = startdate
        while d <= enddate:
            res = self.food_entries.get(date=fs_date(d))
            if res['food_entries']:
                for entry in res['food_entries']['food_entry']:
                    del entry['date_int']
                    entry['date'] = d.strftime("%Y-%m-%d")
                    food_entries += [entry]
            d += timedelta(days=1)
            time.sleep(self.delay)
        return (food_entries, fields)
    
    def get_exercises(self, startdate, enddate):
        fields = ['date',
                  'exercise_id',
                  'exercise_name',
                  'minutes',
                  'calories',
                  'is_template_value']

        exercise_entries = [] 
        d = startdate
        while d <= enddate:
            res = self.exercise_entries.get(date=fs_date(d))
            if res['exercise_entries']:
                for entry in res['exercise_entries']['exercise_entry']:
                    entry['date'] = d.strftime("%Y-%m-%d")
                    exercise_entries += [entry]
            d += timedelta(days=1)
            time.sleep(self.delay)
        return (exercise_entries, fields)

    def get_weight(self, startdate, enddate):
        fields = ['date', 'weight_kg']
        wgt_entries = []
        start = fs_date(startdate)
        end = fs_date(enddate)
        d = start
        while d <= end:
            res = self.weights.get_month(date=d)
            if 'day' in res['month']:
                days = res['month']['day']
                ## if only one day, it is not a list
                if isinstance(days, dict):
                    days = [days]
                for x in days:
                    dt = int(x['date_int'])
                    if dt >= start and dt <= end:
                        x['date'] = dateint2date(dt).strftime("%Y-%m-%d")
                        del x['date_int']
                        wgt_entries += [x]
            d = int(res['month']['to_date_int']) + 1
            time.sleep(self.delay)
        return (wgt_entries, fields)

def create_client():
    config = ConfigParser.ConfigParser()
    config.read(CONFIG)
    
    key = config.get('consumer', 'key')
    secret = config.get('consumer', 'secret')
    username = config.get('user', 'name')
    datastore = config.get('user', 'datastore')

    myapp = FatSecretApplication(key, secret)

    client = NewFatSecretClient().connect()
    client.application=myapp
    client.datastore = TokenShelf(datastore)
    client.authorize(username)
    return client


def fs_date(d):
    """ Return integer as the number of days since Jan 1, 1970"""
    return d.toordinal() - FSEpoch.toordinal()


def dateint2date(d):
    """Convert number of days since Jan 1, 1970 to date"""
    return date.fromordinal(d + FSEpoch.toordinal())


def strptime(string, format):
    """ strptime that returns a date object"""
    return date(*time.strptime(string, format)[0:3])

    
if __name__ == "__main__":
    datefmt = "%Y-%m-%d"
    
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="write output to FILE", metavar="FILE")
    parser.add_option("-s", "--start-date", dest="startdate",
                      default=date.today().strftime(datefmt),
                      help="write output to FILE")
    parser.add_option("-e", "--end-date", dest="enddate",
                      default=date.today().strftime(datefmt),
                      help="write output to FILE")
    (options, args) = parser.parse_args(args=None, values=None)

    ## Output file
    if options.filename:
        f = open(options.filename, 'w')
    else:
        f = sys.stdout

    ## Data to download
    data = args[0]

    ## Dates
    d0 = strptime(options.startdate, datefmt)
    dT = strptime(options.enddate, datefmt)
    ## just correct dates if in wrong order
    if d0 > dT:
        d0, dT = dT, d0

    ## initialize the fatsecret client
    client = create_client()
    
    if data == "food":
        result, fields = client.get_food(d0, dT)
    elif data == "exercise":
        result, fields = client.get_exercises(d0, dT)
    elif data == "weight":
        result, fields = client.get_weight(d0, dT)
    else:
        sys.exit("%s is not a valid data type." % data)

    writer = csv.DictWriter(f, fields)
    writer.writerow(dict( zip(fields, fields)))
    writer.writerows(result)
    f.close()

