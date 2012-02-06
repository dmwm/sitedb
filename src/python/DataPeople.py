from SiteDB.RESTServer import RESTEntity, restcall
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *
from operator import itemgetter
import cherrypy

class People(RESTEntity):
  """REST entity object for people information.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *email*              primary e-mail address    string matching :obj:`.RX_EMAIL`     required, unique
  *forename*           first name                string matching :obj:`.RX_NAME`      required
  *surname*            family name               string matching :obj:`.RX_NAME`      required
  *dn*                 grid certificate subject  string matching :obj:`.RX_DN`        optional
  *username*           account name              string matching :obj:`.RX_USER`      optional, unique
  *phone1*             primary phone number      string matching :obj:`.RX_PHONE`     optional
  *phone2*             secondary phone number    string matching :obj:`.RX_PHONE`     optional
  *im_handle*          instant messaging handle  string matching :obj:`.RX_IM`        optional
  ==================== ========================= ==================================== ====================

  The *username* must be either a CERN account, or a CMS HyperNews external
  account."""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'POST'):
      validate_strlist('email',     param, safe, RX_EMAIL)
      validate_ustrlist('forename',  param, safe, RX_NAME)
      validate_ustrlist('surname',   param, safe, RX_NAME)
      validate_ustrlist('dn',        param, safe, RX_DN)
      validate_strlist('username',  param, safe, RX_USER)
      validate_strlist('phone1',    param, safe, RX_PHONE)
      validate_strlist('phone2',    param, safe, RX_PHONE)
      validate_strlist('im_handle', param, safe, RX_IM)
      validate_lengths(safe, 'email', 'forename', 'surname', 'dn',
                       'username', 'phone1', 'phone2', 'im_handle')
      me = cherrypy.request.user['login']
      for user in safe.kwargs['username']:
        user == me or authz_match(role=["Global Admin"], group=["global"])

    elif method == 'DELETE':
      validate_strlist('email', param, safe, RX_EMAIL)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve people. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *email*
    :returns: sequence of rows of people; field order in the
              returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), """
      select email, to_nchar(forename) forename, to_nchar(surname) surname,
             to_nchar(dn) dn, username, phone1, phone2, im_handle
      from contact
      """)

  @restcall
  def post(self, email, forename, surname, dn, username, phone1, phone2, im_handle):
    """Update the information for a person identified by `email`. A person
    can update their own record, global admins the info for anyone. For input
    validation requirements, see the field descriptions above. When more than
    one argument is given, there must be equal number of arguments for all the
    parameters. It is an error to attempt to update a non-existent `email`.

    :arg list email: accounts to update;
    :arg list forename: new values;
    :arg list surname: new values;
    :arg list dn: new values;
    :arg list username: new values;
    :arg list phone1: new values;
    :arg list phone1: new values;
    :arg list im_handle: new values.
    :returns: a list with a dict in which *modified* gives number of objects
              updated in the database, which is always *len(email).*"""
    return self.api.modify("""
      update contact
      set forename = :forename,
          surname = :surname,
          dn = :dn,
          username = :username,
          phone1 = :phone1,
          phone2 = :phone2,
          im_handle = :im_handle
      where email = :email
      """, email = email, forename = forename, surname = surname, dn = dn,
      username = username, phone1 = phone1, phone2 = phone2, im_handle = im_handle)

  @restcall
  def put(self, email, forename, surname, dn, username, phone1, phone2, im_handle):
    """Insert new people. A person can insert their own record, global admins
    the info for anyone. For input validation requirements, see the field
    descriptions above. When more than one argument is given, there must be
    equal number of arguments for all the parameters. It is an error to
    attempt to insert an already existing `email`.

    :arg list email: accounts to insert;
    :arg list forename: new values;
    :arg list surname: new values;
    :arg list dn: new values;
    :arg list username: new values;
    :arg list phone1: new values;
    :arg list phone1: new values;
    :arg list im_handle: new values.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(email).*"""
    # FIXME: insert into user_passwd (username, passwd) values (:username, '*')
    return self.api.modify("""
      insert into contact
      (id, email, forename, surname, dn, username, phone1, phone2, im_handle)
      values (contact_sq.nextval, :email, :forename, :surname, :dn,
              :username, :phone1, :phone2, :im_handle)
      """, email = email, forename = forename, surname = surname, dn = dn,
      username = username, phone1 = phone1, phone2 = phone2, im_handle = im_handle)

  @restcall
  def delete(self, email):
    """Delete people records. Only global admin can delete people records.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent `email`.

    :arg list email: accounts to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(email).*"""
    return self.api.modify("""
      delete from contact where email = :email
      """, email = email)
