#!/usr/bin/env python
'''
Non destructive migration from SiteDB1 scheam to SiteDB2 schema.

Created on 3 Sep 2009

@author: metson
'''


from optparse import OptionParser
from WMCore.Database.DBFactory import DBFactory
from WMCore.Database.DBFormatter import DBFormatter
from xml.dom.minidom import parse
import logging
import urllib2

def doOptions():
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                      default=False, help="be verbose")
    parser.add_option("-d", "--database", dest="database", help="""database 
    string of the form of oracle://username:password@tnsName or 
    oracle://username:password@host:port/sidname""", 
                      default="oracle://username:password@tnsName")
    parser.add_option("-c", "--clean", dest="clean", action="store_true", 
                      default=False, help="Clean (drop) the new siteinfo table")
    return parser.parse_args()

def drop_table(conn, table):
    try:
        conn.processData('drop table %s' % table)
    except:
        logger.warning("table already removed")

def create_siteinfo(conn):
    sql = """
create table siteinfo (
  id number(10) not null,
  cms_name varchar(100) not null,
  site_name varchar(100) not null,
  country varchar(100) not null,
  usage varchar(100),
  url varchar(1000),
  logourl varchar(1000),
  constraint pk_siteinfo primary key (id),
  constraint uk_siteinfo unique (cms_name)
)
"""
    try:
        drop_table(conn, 'siteinfo')
        conn.processData(sql)
        return True
    except:
        print "table exists, probably - check the logs"
        return False

def create_sitelinks(conn):
    sql = """
create table sitelinks (
  siteid number(10) not null,
  url varchar(1000)
)
"""
    try:
        drop_table(conn, 'sitelinks')
        conn.processData(sql)
        return True
    except:
        print "table exists, probably - check the logs"
        return False
    
def get_siteinfo(conn):
    formatter = DBFormatter(logging.getLogger('SiteDB Schema Upgrade'), conn)
    sql = """select 
    site.id, 
    cms_name.name cms_name, 
    site.name site_name, 
    site.country, 
    site.usage, 
    site.url, 
    site.logourl from site
join SITE_CMS_NAME_MAP on SITE_CMS_NAME_MAP.SITE_ID=site.id
join CMS_NAME on CMS_NAME.ID = SITE_CMS_NAME_MAP.CMS_NAME_ID
"""
    data = conn.processData(sql)
    return formatter.formatDict(data)
    
def populate_siteinfo(siteinfo, conn):
    badsites = []
    for site in siteinfo:
        sql = """insert into siteinfo 
            (id, cms_name, site_name, country, usage, url, logourl) values
            (:id, :cms_name, :site_name, :country, :usage, :url, :logourl)"""
        try:
            logger.debug("trying %s" % site['cms_name'])
            conn.processData(sql, site)
        except:
            badsites.append(site)
            #badsites = siteinfo
    return badsites
        
def check_badsites(badsites, conn):
    """
    Go through the list of bad sites, check if they are _exactly_ in the DB 
    already. If they are remove them from the badsites list, if not leave them 
    in purgatory.
    """
    for constraint in ['cms_name', 'id']:
        formatter = DBFormatter(logger, conn)
        sql = "select * from siteinfo where %s = :%s" % (constraint, constraint)
        for site in badsites:
            try:
                data = conn.processData(sql, {constraint: site[constraint]})
                test = formatter.formatDict(data)[0]
                if test == site:
                    logger.debug("%s actually did make it..." % site['cms_name'])
                    badsites.remove(site)
            except:
                logger.warning("%s really didn't make it..." % site['cms_name'])
    return badsites        

def check_sites(oldsites, badsites, conn):
    """
    Make sure that all sites from the old schema, that aren't in bad sites are 
    in the new schema.
    """
    logger = logging.getLogger('SiteDB Schema Upgrade: check_sites')
    sql = "select * from siteinfo where cms_name = :cms_name"
    formatter = DBFormatter(logger, conn)
    print "checking %s sites" % len(oldsites)
    for site in oldsites:
        test = None
        if not site in badsites:
            try:
                data = conn.processData(sql, {'cms_name': site['cms_name']})
                test = formatter.formatDict(data)
                if len(test) > 0: 
                    testsite = test[0] 
                    if testsite == site:
                        logger.debug("%s migrated correctly!" % site['cms_name'])
                    else:
                        logger.warning("Problem with %s" % site['cms_name'])
                        logger.warning("%s != %s" % (testsite, site))
                    
                else:
                    logger.warning("Problem with %s" % site['cms_name'])
                    logger.warning("%s != %s" % (test, site))
                    
            except Exception, e:
                logger.warning("Problem with %s" % site['cms_name'])
                logger.warning("%s != %s" % (test, site))
                logger.warning(e)
    return badsites

def migrate_badsites(badsites, conn):
    awfulsites = []
    goodsites = []
    for site in badsites:
        sql = """insert into siteinfo 
            (id, cms_name, site_name, country, usage, url, logourl) values
            (site_sq.nextval, :cms_name, :site_name, :country, :usage, :url, :logourl)"""
        try:
            logger.debug("trying %s" % site['cms_name'])
            oldid = site['id']
            del site['id']
            conn.processData(sql, site)
            formatter = DBFormatter(logger, conn)
            data = conn.processData("select id from siteinfo where cms_name=:cms_name", 
                             {'cms_name':site['cms_name']})
            data = formatter.formatOneDict(data)
            print data
            logger.warning("%s migrated with a new id: %s" % (site['cms_name'],
                                                              data['id']))
            goodsites.append(site)
        except Exception, e:
            awfulsites.append(site)
            logger.warning(e)
    return awfulsites, goodsites

if __name__ == "__main__":
    opts, args = doOptions()
    conn = None
    if opts.verbose:
        print logging.DEBUG
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
    else:
        logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
    
    logger = logging.getLogger('SiteDB Schema Upgrade')

    #Connect to the database
    
    conn = DBFactory(logger, opts.database).connect()
    logger.debug('connected to %s' % opts.database)
    oldsites = get_siteinfo(conn)
    logger.debug(oldsites)
    
    if create_siteinfo(conn):
        if create_sitelinks(conn):
            badsites = populate_siteinfo(oldsites, conn)
            logger.debug(badsites)
            badsites = check_badsites(badsites, conn)
            badsites = check_sites(oldsites, badsites, conn)
            print "trying to migrate %s bad sites" % len(badsites) 
            badsites, goodsites = migrate_badsites(badsites, conn)
        
            if len(badsites):
                badsites = check_sites(goodsites, badsites, conn)
            if len(badsites):
                print "couldn't migrate the following sites:\n%s" % badsites