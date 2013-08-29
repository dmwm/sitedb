from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class FederationsPledges(RESTEntity):
  """Entity object for federations pledges and federations names insert from rebus.

==================== ========================= ==================================== ====================
Contents             Meaning                   Value                                Constraints
==================== ========================= ==================================== ====================
*name*               name title string         matching :obj:`.RX_LABEL`            required, unique
==================== ========================= ==================================== ====================
"""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT'):
      validate_strlist('name', param, safe, RX_FEDERATION)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve federations pledges. The results aren't ordered in any particular way.

       :arg str match: optional regular expression to filter by *title*

       :returns: sequence of rows of federations names; field order in the
                 returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), """select afn.name, afn.country, fp.year, fp.cpu, fp.disk, fp.tape,
                                                          (cast(sys_extract_utc(fp.feddate) as date)
                                                                - to_date('19700101', 'YYYYMMDD')) *86400 feddate
                                                          from federations_pledges fp
                                                          join all_federations_names afn on afn.id = fp.federations_names_id
                                                          order by afn.country, afn.name, fp.feddate ASC""");

  @restcall
  def put(self, name):
    """Insert new federations name from REBUS. The caller needs to have global admin privileges.
       For input validation requirements, see the field descriptions above.
       It is an error to attempt to insert a federation name from REBUS which already exists.

       :arg list title: names to insert.

       :returns: a list with a dict in which *modified* gives number of objects
                 inserted into the database, which is always *len(name).*"""
    return self.api.modify("""
      insert into federations_names (name, id)
      values (:name, federations_names_sq.nextval)
      """, name = name)
