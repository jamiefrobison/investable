# -*- coding: utf-8 -*-

from scrapy.exceptions import DropItem
import re
import urllib
import geocoder
# import imp
# import json

# model = imp.load_source('model.py', '../../')
from model import connect_to_db_scrapy, Rental, UnitDetails


class RentScraperPipeline(object):
    """ Scrubs scraped data of whitespaces and interesting characters and returns it as a data maintenance-friendly dictionary. """

    def process_item(self, item, spider):

        # Gets Craigslist posting ID
        if item['cl_id']:
            item['cl_id'] = re.split('\s', ''.join(item['cl_id']))[2]

        # Finds rental price; if none supplied or if it's listed below $50, drop item
        if item['price']:
            price = int(re.sub('[^\d.]+', '', ''.join(item['price'])))
            if price > 50:
                item['price'] = price
            else:
                raise DropItem('Missing price in %s' % item)
        else:
            raise DropItem('Missing price in %s' % item)

        # Finds bedrooms, bathrooms, and sqft, if provided
        if item['attributes']:
            attrs = item['attributes']

            for i, attribute in enumerate(attrs):
                if "BR" in attrs[i]:
                    item['bedrooms'] = float(''.join(re.findall('\d+\.*\d*', attrs[i])))
                if "Ba" in attrs[i]:
                    item['bathrooms'] = float(''.join(re.findall('\d+\.*\d*', attrs[i])))
                if "BR" not in attrs[i] and "Ba" not in attrs[i]:
                    item['sqft'] = int(attrs[i])

        # Get neighborhood name, if provided
        if item['neighborhood']:
            item['neighborhood'] = re.sub('[^\s\w/\.]+', '', ''.join(item['neighborhood'])).rstrip().lstrip()

        # Get posting date in UTC isoformat time
        if item['date']:
            item['date'] = ''.join(item['date'])

        # Find Google maps web address; if none exists drop record
        if item['location']:
            location_url = urllib.unquote(''.join(item['location'])).decode('utf8')
            find_location = location_url.split('loc:')

            # If location on map is found convert to geolocation; if none exists drop record
            if len(find_location) > 1:
                location = find_location[1]
                geo_location = geocoder.google(location)

            # If a geocoded location exists get latitude and longitude, otherwise drop record
                if geo_location:
                    latitude = geo_location.lat
                    longitude = geo_location.lng
                    item['latitude'] = latitude
                    item['longitude'] = longitude
                    item['latlng'] = 'POINT(%s %s)' % (latitude, longitude)
                else:
                    raise DropItem('Missing geolocation in %s' % item)

            else:
                raise DropItem('Missing google maps location in %s' % item)

        else:
            raise DropItem('Missing google maps web address in %s' % item)

        return item


# class JsonWriterPipeline(object):
#     """ Takes scrubbed data and outputs as JSON Lines file. Only used for creating a seed file for test database. """

#     def open_spider(self, spider):
#         self.file = open('test.jl', 'wb')

#     def close_spider(self, spider):
#         self.file.close()

#     def process_item(self, item, spider):
#         line = json.dumps(dict(item)) + '\n'
#         self.file.write(line)
#         return item


class PostgresqlPipeline(object):
    """ Writes data to PostgreSQL database. """

    def __init__(self):
        """ Initializes database connection. """

        self.session = connect_to_db_scrapy()


    def process_item(self, item, spider):
        """ Method used to write data to database directly from the scraper pipeline. """

        cl_id = item.get('cl_id')
        price = item.get('price')
        date = item.get('date')
        neighborhood = item.get('neighborhood')
        bedrooms = item.get('bedrooms')
        bathrooms = item.get('bathrooms')
        sqft = item.get('sqft')
        latitude = item.get('latitude')
        longitude = item.get('longitude')
        latlng = item.get('latlng')

        try:
            # Create rental details for unit
            rental_details = UnitDetails(
                                neighborhood=neighborhood,
                                bedrooms=bedrooms,
                                bathrooms=bathrooms,
                                sqft=sqft,
                                latitude=latitude,
                                longitude=longitude,
                                latlng=latlng
                            )

            # Add rental details to UnitDetails table
            self.session.add(rental_details)

            # Create rental unit
            rental = Rental(
                        cl_id=cl_id,
                        price=price,
                        date_posted=date,
                        unitdetails=rental_details
                    )

            # Add rental unit to Rental table
            self.session.add(rental)

            self.session.commit()

        except:
            # If the unit already exists in db or if data does not fit db construct
            self.session.rollback()
            raise

        finally:
            self.session.close()


    # def load_seed_file(self):
    #     """ Method used to write JSON Lines file data to database, if necessary. Should prioritize use of load_data_from_scraper method instead for direct data handling. """

    #     for row in open('test.jl'):
    #         row = row.rstrip()

    #         cl_id = row['cl_id']
    #         price = row['price']
    #         date = row['date']
    #         neighborhood = row['neighborhood']
    #         bedrooms = row['bedrooms']
    #         bathrooms = row['bathrooms']
    #         sqft = row['sqft']
    #         latlng = row['latlng']

    #         # Add rental details to UnitDetails table
    #         rental_details = UnitDetails(
    #                             neighborhood=neighborhood,
    #                             bedrooms=bedrooms,
    #                             bathrooms=bathrooms,
    #                             sqft=sqft,
    #                             latlng=latlng
    #                         )

    #         db.session.add(rental_details)

    #         # Add rental unit to Rentals table
    #         rental = Rental(
    #                     cl_id=cl_id,
    #                     price=price,
    #                     date_posted=date,
    #                     unitdetails=rental_details
    #                 )

    #         db.session.add(rental)

    #         db.session.commit()
