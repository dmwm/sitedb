from WMCore.Configuration import Configuration
from os import environ, path
import sys
config = Configuration()

# This component has all the configuration of CherryPy
config.component_('Webtools')

# This is the application
config.Webtools.application = 'SiteDB'
config.Webtools.port = 8010
# This is the config for the application
config.component_('SiteDB')
config.SiteDB.admin = 'your@email.com'
config.SiteDB.title = 'CMS SiteDB'
config.SiteDB.description = 'A database of sites known to CMS'


# Define the default location for templates for the app
if 'SITEDBBASE' not in environ.keys():
    basepath = path.abspath(sys.argv[2]).split('src')[0] + 'src'
    environ['SITEDBBASE'] = basepath
config.SiteDB.templates = environ['SITEDBBASE'] + '/templates/SiteDB/'
# Define the class that is the applications index
#config.SiteDB.index = 'sites'

config.SiteDB.section_('services')
config.SiteDB.services.savannah = 'https://savannah.cern.ch'
config.SiteDB.services.phedex = 'http://cmsweb.cern.ch/phedex/prod/Request::Create?dest='
config.SiteDB.services.dbs = 'https://cmsweb.cern.ch/dbs_discovery/getData?dbsInst=cms_dbs_prod_global&proc=&ajax=0&userMode=user&group=*&tier=*&app=*&site'
config.SiteDB.services.goc = 'https://goc.gridops.org/site/list?id='
config.SiteDB.services.gstat = 'http://goc.grid.sinica.edu.tw/gstat'
config.SiteDB.services.dashboard = 'http://lxarda16.cern.ch/dashboard/request.py'
config.SiteDB.services.squid = 'http://frontier.cern.ch/squidstats/mrtgcms'
config.SiteDB.services.sam = 'https://lcg-sam.cern.ch:8443/sam/sam.py?'
config.SiteDB.services.cachepath = '/tmp'
config.SiteDB.services.hostcert = ''
config.SiteDB.services.hostkey = ''

# Views are all pages 
config.SiteDB.section_('views')
# These are all the active pages that Root.py should instantiate 
active = config.SiteDB.views.section_('active')

# These are pages in "maintenance mode" - to be completed
maint = config.SiteDB.views.section_('maintenance')

active.section_('sites')
active.sites.object = 'WMCore.WebTools.RESTApi'
active.sites.authenticate = True
active.sites.authorise = True
active.sites.templates = environ['WMCORE_ROOT'] + '/src/templates/WMCore/WebTools'
active.sites.section_('model')
active.sites.model.object = 'SiteDB.REST.Sites.Base'
active.sites.section_('formatter')
active.sites.formatter.object = 'WMCore.WebTools.RESTFormatter'
active.sites.section_('database')
active.sites.database.connectUrl = 'oracle://username:password@database'

active.section_('people')
active.people.object = 'WMCore.WebTools.RESTApi'
active.people.authenticate = True
active.people.authorise = True
active.people.templates = environ['WMCORE_ROOT'] + '/src/templates/WMCore/WebTools'
active.people.section_('model')
active.people.model.object = 'SiteDB.REST.People.Base'
active.people.section_('formatter')
active.people.formatter.object = 'WMCore.WebTools.RESTFormatter'
active.people.section_('database')
active.people.database.connectUrl = 'oracle://username:password@database'
