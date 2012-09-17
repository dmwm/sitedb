from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter
from cherrypy import HTTPError
import cherrypy

class People(RESTEntity):
  """REST entity object for people information.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *username*           account name              string matching :obj:`.RX_USER`      required, unique
  *email*              primary e-mail address    string matching :obj:`.RX_EMAIL`     required, unique
  *forename*           first name                string matching :obj:`.RX_NAME`      required
  *surname*            family name               string matching :obj:`.RX_NAME`      required
  *dn*                 grid certificate subject  string matching :obj:`.RX_DN`        optional
  *phone1*             primary phone number      string matching :obj:`.RX_PHONE`     optional
  *phone2*             secondary phone number    string matching :obj:`.RX_PHONE`     optional
  *im_handle*          instant messaging handle  string matching :obj:`.RX_IM`        optional
  ==================== ========================= ==================================== ====================

  The *username* must be either a CERN account, or a CMS HyperNews external
  account, or a pseudo-account for services."""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'POST'):
      validate_strlist('username',  param, safe, RX_USER)
      validate_strlist('email',     param, safe, RX_EMAIL)
      validate_ustrlist('forename',  param, safe, RX_NAME)
      validate_ustrlist('surname',   param, safe, RX_NAME)
      validate_ustrlist('dn',        param, safe, RX_DN)
      validate_strlist('phone1',    param, safe, RX_PHONE)
      validate_strlist('phone2',    param, safe, RX_PHONE)
      validate_strlist('im_handle', param, safe, RX_IM)
      validate_lengths(safe, 'username', 'email', 'forename', 'surname',
                       'dn', 'phone1', 'phone2', 'im_handle')

      mydn = cherrypy.request.user['dn']
      me = cherrypy.request.user['login']
      for user, dn in zip(safe.kwargs['username'], safe.kwargs['dn']):
        if (method != 'POST' or user != me or dn != mydn):
          try:
            authz_match(role=["Global Admin"], group=["global"])
          except HTTPError:
            authz_match(role=["Operator"], group=["SiteDB"])

    elif method == 'DELETE':
      validate_strlist('username',  param, safe, RX_USER)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve people. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *username*
    :returns: sequence of rows of people; field order in the
              returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), """
      select username, email, to_nchar(forename) forename,
             to_nchar(surname) surname, to_nchar(dn) dn,
             phone1, phone2, im_handle
      from contact
      """)

  @restcall
  def post(self, username, email, forename, surname, dn, phone1, phone2, im_handle):
    """Update the information for a person identified by `username`. A person
    can update their own record except not alter the DN information, global
    admins the info for anyone. For input validation requirements, see the
    field descriptions above. When more than one argument is given, there
    must be equal number of arguments for all the parameters. It is an error
    to attempt to update a non-existent `username`.

    :arg list username: accounts to update;
    :arg list email: new values;
    :arg list forename: new values;
    :arg list surname: new values;
    :arg list dn: new values;
    :arg list phone1: new values;
    :arg list phone1: new values;
    :arg list im_handle: new values.
    :returns: a list with a dict in which *modified* gives number of objects
              updated in the database, which is always *len(username).*"""
    return self.api.modify("""
      update contact
      set email = :email,
          forename = :forename,
          surname = :surname,
          dn = :dn,
          phone1 = :phone1,
          phone2 = :phone2,
          im_handle = :im_handle
      where username = :username
      """, username = username, email = email, forename = forename, surname = surname,
      dn = dn, phone1 = phone1, phone2 = phone2, im_handle = im_handle)

  @restcall
  def put(self, username, email, forename, surname, dn, phone1, phone2, im_handle):
    """Insert new people. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above. When
    more than one argument is given, there must be equal number of arguments
    for all the parameters. It is an error to attempt to insert an already
    existing `username`.

    :arg list username: accounts to insert;
    :arg list email: new values;
    :arg list forename: new values;
    :arg list surname: new values;
    :arg list dn: new values;
    :arg list phone1: new values;
    :arg list phone1: new values;
    :arg list im_handle: new values.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(username).*"""
    c, _ = self.api.executemany("""
      merge into user_passwd u using dual on (u.username = :username)
      when not matched then insert (username, passwd) values (:username, '*')
      """, self.api.bindmap(username = username))

    return self.api.modify("""
      insert into contact
      (id, username, email, forename, surname, dn, phone1, phone2, im_handle)
      values (contact_sq.nextval, :username, :email, :forename, :surname,
              :dn, :phone1, :phone2, :im_handle)
      """, username = username, email = email, forename = forename, surname = surname,
      dn = dn, phone1 = phone1, phone2 = phone2, im_handle = im_handle)

  @restcall
  def delete(self, username):
    """Delete people records. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent `username`.

    :arg list username: accounts to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(username).*"""
    return self.api.modify("""
      delete from contact where username = :username
      """, username = username)
