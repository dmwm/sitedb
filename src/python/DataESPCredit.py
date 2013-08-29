from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class ESPCredit(RESTEntity):
  """Entity object for ESP Credits.

==================== ========================= ==================================== ====================
Contents             Meaning                   Value                                Constraints
==================== ========================= ==================================== ====================
*site*               site name canonical       string matching `.RX_LABEL`          required
*value*              ESP Credit value          real, >=0                            required
*year*               Year of esp credit input  date year 4 digits                   required
==================== ========================= ==================================== ====================
"""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT'):
      validate_strlist('site', param, safe, RX_LABEL)
      validate_reallist('value', param, safe, minval = 0.)
      validate_strlist('year', param, safe, RX_YEARS)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve all sites ESP Credits values and years. The results aren`t ordered in any particular way

    :arg str match: optional regular expression to filter by *site*
    :returns: sequence of rows of ESP Credits. field order in the returned *desc.columns*"""
    return self.api.query(match, itemgetter(0), """
      select id, site, year, esp_credit from sites_esp_credits""");

  @restcall
  def put(self, site, value, year):
    """Insert new ESP Credit value, or update old one. History is not implemented. Always rewriting and showing the newest value

    :arg list site: site canonical name;
    :arg list value: new values;
    :arg list year: new values;
    :returns: a list with dict in which *modified* gives number of objects updated or
              inserted in database"""
    current = {}
    siten = site[0]
    valuen = value[0]
    yearn = year[0]
    c, _ = self.api.execute("""select site, year, esp_credit from sites_esp_credits""")
    for row in c:
      site_r, year_r, esp_credit_r = row
      if site_r in current.keys():
        if year_r in current[site_r].keys():
          cherrypy.log('ERROR, Dublicate value in database!')
        else:
          current[site_r][str(year_r)] = {'espcredit': esp_credit_r };
      else:
        current[site_r] = {str(year_r) : {'espcredit': esp_credit_r}};
    cherrypy.log('ALL from database %s' % current.keys())
    if siten in current.keys():
      if yearn in current[siten].keys():
        return self.api.modify("""update sites_esp_credits set esp_credit = :esp_credit where site= :site and year = :year """,
                             esp_credit = value, site = site, year = year)
      else:
        return self.api.modify("""Insert into sites_esp_credits(id, site, year, esp_credit)
                           values(sites_esp_credits_sq.nextval, :site, :year, :esp_credit)
                        """, site = site, year = year, esp_credit = value)
    else:
      return self.api.modify("""Insert into sites_esp_credits(id, site, year, esp_credit)
                         values(sites_esp_credits_sq.nextval, :site, :year, :esp_credit)
                      """, site = site, year = year, esp_credit = value)
