from woocommerce import API
import time
from functools import wraps
import json, locale, logging, urllib, ConfigParser, sys, csv

locale.setlocale(locale.LC_ALL, 'hu_HU.UTF-8')

logging.basicConfig(format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s", level=logging.DEBUG) #, #filename='fp.log')
log = logging.getLogger(__name__)

config = ConfigParser.ConfigParser()
config.readfp(open(sys.path[0]+'/import.cfg'))
token = config.get("default", "ecwid_token")
shopid = config.get("default", "ecwid_shopid")
ofilePath = config.get("default", "ofilePath")

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry

# See: https://stackoverflow.com/questions/9446387/how-to-retry-urllib2-request-when-fails
@retry(IOError, tries=3, delay=10, backoff=2, logger=log)
def getProductforSku(sku):
    url = "https://app.ecwid.com/api/v3/" + shopid + "/products?token=" + token + "&sku=" +sku
    r = urllib.urlopen(url).read()
    return json.loads(r)

#https://pypi.python.org/pypi/WooCommerce
wcapi = API(
    url=config.get("default", "woo_url"),
    consumer_key=config.get("default", "woo_consumer_key"),
    consumer_secret=config.get("default", "woo_consumer_secret"),
    wp_api=True,
    version="wc/v1",
    timeout=30
)


ofile = open(ofilePath, "wb")
owriter = csv.writer(ofile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
owriter.writerow([ 'old_url', "old_sku", 'sku', 'new_url' ])

# See: http://woocommerce.github.io/woocommerce-rest-api-docs#products
# See also: http://woocommerce.github.io/woocommerce-rest-api-docs/#pagination
for page in [1,2,3]:
    r = wcapi.get("products?per_page=100&page=" + str(page) )

    log.info( r.status_code )

    products = json.loads(r.text)

    log.info( len(products) )

    for product in products:
        log.info("Product: %s" % [product['sku'], product['permalink'].encode('utf-8') ])
        sku = product['sku'].split('-')[0]
        ecwid_items= getProductforSku(sku)["items"]
        if ( len(ecwid_items) >1 ):
            log.warn("More than 1 items for SKU: %1", sku)
        log.info("Ecwid Product: %s" % [ecwid_items[0]['sku'], ecwid_items[0]['url'].encode('utf-8') ])
        owriter.writerow([ecwid_items[0]['url'].encode('utf-8'), ecwid_items[0]['sku'], product['sku'], product['permalink'] ])

ofile.close()