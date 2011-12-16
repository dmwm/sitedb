from WMCore.Configuration import Configuration

class Config(Configuration):
  """Default SiteDB server configuration."""
  def __init__(self, db = None, authkey = None, nthreads = 5, port = 8051):
    """
    :arg str db: Location of database configuration, "module.object". Defaults
      to "SiteDBAuth.dbparam".
    :arg str authkey: Location of wmcore security header authentication key.
    :arg integer nthreads: Number of server threads to create.
    :arg integer port: Server port."""

    Configuration.__init__(self)
    main = self.section_('main')
    srv = main.section_('server')
    srv.thread_pool = nthreads
    main.application = 'sitedb'
    main.port = port
    main.index = 'ui'

    main.authz_defaults = { 'role': None, 'group': None, 'site': None }
    sec = main.section_('tools').section_("cms_auth")
    sec.key_file = authkey

    app = self.section_('sitedb')
    app.admin = 'cms-service-webtools@cern.ch'
    app.description = 'A database of sites known to CMS'
    app.title = 'CMS SiteDB'

    views = self.section_('views')
    ui = views.section_('ui')
    ui.object = 'SiteDB.FrontPage.FrontPage'

    data = views.section_('data')
    data.object = 'SiteDB.Data.Data'
    data.db = db or 'SiteDBAuth.dbparam'
