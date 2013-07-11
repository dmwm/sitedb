from WMCore.REST.Server import RESTEntity, restcall
from SiteDB.SiteAuth import oldsite_authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class Pledges(RESTEntity):
  """REST entity object for site resource pledges.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *site_name*          site name                 string matching :obj:`.RX_SITE`      required, unique
  *date*               date the pledge was made  real, unix epoch time stamp          listed on read
  *quarter*            quarter                   string matching :obj:`.RX_QUARTER`   required
  *cpu*                total cpu capacity, kHS06 real, >= 0                           optional
  *job_slots*          number of job slots       real, >= 0                           optional
  *disk_store*         disk capacity, TB         real, >= 0                           optional
  *tape_store*         tape capacity, TB         real, >= 0                           optional
  *wan_store*          wan buffer capacity, TB   real, >= 0                           optional
  *local_store*        local disk capacty, TB    real, >= 0                           optional
  *national_bandwidth* national bandwidth, Gbps  real, >= 0                           optional
  *opn_bandwidth*      lcg opn bandwidth, Gbps   real, >= 0                           optional
  ==================== ========================= ==================================== ====================

  All pledges made are recorded in the database. Hence pledges cannot be
  updated or deleted as such, the site simply makes a new pledge for the
  same quarter to override the previous pledge. All pledges made are saved
  with the time stamp of the creation time; this is supplied automatically
  and is not given by the client, and is automatically returned on reads.

  On read, all pledges made by the site are returned in increasing pledge
  date and quarter order. To obtain the current pledge for each quarter the
  client should keep just the last pledge for that quarter."""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method == 'PUT':
      validate_strlist('site_name',           param, safe, RX_SITE)
      validate_strlist('quarter',             param, safe, RX_QUARTER)
      validate_reallist('cpu',                param, safe, minval = 0.)
      validate_reallist('job_slots',          param, safe, minval = 0.)
      validate_reallist('disk_store',         param, safe, minval = 0.)
      validate_reallist('tape_store',         param, safe, minval = 0.)
      validate_reallist('wan_store',          param, safe, minval = 0.)
      validate_reallist('local_store',        param, safe, minval = 0.)
      validate_reallist('national_bandwidth', param, safe, minval = 0.)
      validate_reallist('opn_bandwidth',      param, safe, minval = 0.)
      validate_lengths(safe, 'site_name', 'quarter', 'cpu', 'job_slots',
                       'disk_store', 'tape_store', 'wan_store', 'local_store',
                       'national_bandwidth', 'opn_bandwidth')
      # Delay authz until we have database connection for name remapping.

  def _authz(self, sites):
    """Run late authorisation, remapping site names to canonical ones."""
    remap = {}
    for site in sites:
      oldsite_authz_match(self.api, remap,
                          role=["Global Admin", "Site Executive"],
                          group=["global"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve pledges. The results aren't ordered in any particular
    way except that for any given site's quarter, they are ordered by
    increasing pledge date, i.e. last entry for a site's quarter is the
    "current" one.

    :arg str match: optional regular expression to filter by *site_name*
    :returns: sequence of rows of pledges; field order in the
              returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), """
      select s.name site_name,
             (cast(sys_extract_utc(rp.pledgedate) as date)
              - to_date('19700101', 'YYYYMMDD')) *86400 pledge_date,
             rp.pledgequarter quarter,
             rp.cpu, rp.job_slots, rp.disk_store,
             rp.tape_store, rp.wan_store, rp.local_store,
             rp.national_bandwidth, rp.opn_bandwidth
      from resource_pledge rp
      join site s on s.id = rp.site
      order by s.name, rp.pledgedate, rp.pledgequarter
      """)

  @restcall
  def put(self, site_name, quarter, cpu, job_slots,
          disk_store, tape_store, wan_store, local_store,
          national_bandwidth, opn_bandwidth):
    """Insert new pledge for *site_name* and *quarter*. A site executive /
    admin can insert pledges for their own site, the global admins for all
    sites.  For input validation requirements, see the field descriptions
    above. When more than one argument is given, there must be equal number
    of arguments for all the parameters.

    :arg list site_name: sites for which to insert pledges;
    :arg list quarter: quarters for which to insert pledges;
    :arg list cpu: new values;
    :arg list job_slots: new values;
    :arg list disk_store: new values;
    :arg list tape_store: new values;
    :arg list wan_store: new values;
    :arg list local_store: new values;
    :arg list national_bandwidth: new values;
    :arg list opn_bandwidth: new values.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(site_name).*"""
    self._authz(site_name)
    return self.api.modify("""
      insert into resource_pledge
        (pledgeid, site, pledgedate, pledgequarter, cpu, job_slots,
         disk_store, tape_store, wan_store, local_store,
         national_bandwidth, opn_bandwidth)
      values
        (resource_pledge_sq.nextval,
         (select id from site where name = :site_name),
         systimestamp, :quarter, :cpu, :job_slots,
         :disk_store, :tape_store, :wan_store, :local_store,
         :national_bandwidth, :opn_bandwidth)
      """, site_name=site_name, quarter=quarter, cpu=cpu, job_slots=job_slots,
      disk_store=disk_store, tape_store=tape_store,
      wan_store=wan_store, local_store=local_store,
      national_bandwidth=national_bandwidth, opn_bandwidth=opn_bandwidth)
