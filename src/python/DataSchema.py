from SiteDB.RESTServer import RESTEntity, restcall
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *
from operator import itemgetter
from os.path import join as joinpath
import os, string, random

# Utility to generate new passwords for roles.
def mkpasswd():
  passchars = string.letters + string.digits
  return ''.join(random.choice(passchars) for _ in xrange(10))

class Schema(RESTEntity):
  def __init__(self, *args):
    RESTEntity.__init__(self, *args)
    self._schemadir = joinpath(os.getcwd(), "src/sql")
    self._schema = open(joinpath(self._schemadir, "sitedb.sql")).read()

  """REST entity object for database schema."""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method == 'POST':
      validate_str('action', param, safe, re.compile(r"^(archive|restore)$"))
    elif method == 'DELETE':
      validate_str('action', param, safe, re.compile(r"^(all|archive|current)$"))

    authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=3600)
  def get(self):
    """Retrieve schema description."""
    rows = []
    statements = [
      # Configure DBMS_METADATA. BEGIN ... END avoids PL/SQL procedure bind.
      # NOTE: If SiteDB schema acquires storage specs, switch them on here!
      "begin"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'PRETTY', true);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'STORAGE', false);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'TABLESPACE', false);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'SQLTERMINATOR', true);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'REF_CONSTRAINTS', false);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'CONSTRAINTS_AS_ALTER', false);"
      "end;",

      # Retrieve tables, but not backing tables for materialized views. Get
      # tables without referential constraints because we cannot control the
      # order in which tables are retrieved, so we need to prevent foreign
      # key declarations to tables which don't even exist yet.
      "select dbms_metadata.get_ddl('TABLE', x.object_name) from user_objects x"
      " where object_type = 'TABLE' and not exists (select 1 from user_objects o"
      " where o.object_name = x.object_name and o.object_type = 'MATERIALIZED VIEW')"
      " order by x.object_name",

      # Get all normal indices. Indices created by constraints were already
      # covered above as table constraints so we exclude them here.
      "select dbms_metadata.get_ddl('INDEX', x.index_name) from user_indexes x"
      " where not exists (select 1 from user_constraints c where"
      " c.constraint_name = x.index_name and c.table_name = x.table_name)"
      " order by x.index_name",

      # Fetch rest of object creation clauses.
      "select dbms_metadata.get_ddl(replace(object_type, ' ', '_'), object_name)"
      " from user_objects where object_type in ('SEQUENCE', 'PROCEDURE', 'PACKAGE',"
      " 'PACKAGE BODY', 'MATERIALIZED VIEW', 'VIEW', 'FUNCTION', 'TRIGGER', 'SYNONYM')"
      " order by object_type, object_name",

      # Now create DDL for foreign key referential constraints, targets exist.
      "select dbms_metadata.get_dependent_ddl('REF_CONSTRAINT', table_name) from"
      " (select distinct table_name from user_constraints where constraint_type = 'R')"
      " order by table_name",

      # Finally, dump database links. Annnoyingly the get_ddl() argument name
      # differs from user_objects.object_type so handle this separately.
      "select dbms_metadata.get_ddl('DB_LINK', object_name)"
      " from user_objects where object_type = 'DATABASE LINK'"
      " order by object_name",

      # Retrieve roles. Attempting to access roles directly with get_ddl('ROLE')
      # does not work because the information is only available to DBAs. Expand
      # the DDL manufacturing statements manually, it's not so much.
      "select 'CREATE ROLE ' || granted_role || ' IDENTIFIED BY @PASSWORD@;'"
      " from user_role_privs where admin_option = 'YES'",

      "select 'GRANT ' || privilege || ' TO ' || role ||"
      " (case when admin_option = 'YES' then ' WITH ADMIN OPTION;' else ';' end)"
      " from role_sys_privs where role in (select granted_role from user_role_privs"
      " where admin_option = 'YES')",

      "select 'GRANT ' || granted_role || ' TO ' || role ||"
      " (case when admin_option = 'YES' then ' WITH ADMIN OPTION;' else ';' end)"
      " from role_role_privs where role in (select granted_role from user_role_privs"
      " where admin_option = 'YES')",

      "select 'GRANT ' || privilege || ' ON \"' || owner || '\".\"'"
      " || table_name || '\" TO ' || role ||"
      " (case when grantable = 'YES' then ' WITH GRANT OPTION;' else ';' end)"
      " from role_tab_privs where role in (select granted_role from user_role_privs"
      " where admin_option = 'YES')",

      # Now dump object and system grants plus default role. These generate
      # 'ORA-31608: specified object of type XYZZY not found' if there is no
      # information available of the given type, requiring protection below.
      "select dbms_metadata.get_dependent_ddl('OBJECT_GRANT', x.object_name,"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from user_objects x",

      "select dbms_metadata.get_granted_ddl('SYSTEM_GRANT',"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from dual",

      "select dbms_metadata.get_granted_ddl('DEFAULT_ROLE',"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from dual",

      "select dbms_metadata.get_granted_ddl('ROLE_GRANT',"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from dual",

      # Restore DBMS_METADATA settings.
      "begin dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'DEFAULT'); end;"
    ]

    # Run all statements, and collect any data they produced. If there are
    # any CLOBs from dbms_metadata.get_ddl() type calls, read them in. Fake
    # out passwords from roles with template contents.
    #
    # If we come across "IDENTIFIED BY @PASSWORD@", generate a password.
    # If we got to sys.user$ / dba_roles tables, we could add "IDENTIFED
    # BY VALUES 'xxx'" but we can't get at original hashed passwords, so
    # just fake new passwords for all roles.
    for stmt in statements:
      try:
        c, _ = self.api.execute(stmt)
        if stmt.startswith("select"):
          for text, in c:
            if hasattr(text, 'read'):
              text = text.read()
            while text.upper().find("IDENTIFIED BY @PASSWORD@") >= 0:
              text = text.replace("@PASSWORD@", "FAKE_" + mkpasswd() + "_FAKE", 1)
            rows.append(text)
      except Exception, e:
	# Ignore ORA-31608: specified object of type XYZZY not found
	if not e.args or getattr(e.args[0], 'code', None) != 31608:
	  raise

    return rows

  @restcall
  def post(self, action):
    """Update database schema, i.e. archive current schema out of the way
    or restore archived schema back to main schema.

    The database must contain a schema previously initialised with PUT.
    This operation moves all tables, sequences, indices and constraints
    out of the way by renaming them with a prefix ``X`` (action=archive)
    or removing the prefix ``X`` (action=restore).

    The caller must have global admin privileges.

    :arg str action: update action to perform.
    :returns: series of messages on what was renamed."""
    rows = []
    if action == 'save':
      negate = 'not'
      rename = lambda old: "X%s" % old[0:29]
    elif action == 'restore':
      negate = ''
      rename = lambda old: old[1:]
    else:
      raise RuntimeError("Internal error, invalid 'action'")

    # Rename tables and sequences.
    c, _ = self.api.execute("select object_type, object_name from user_objects"
		            " where object_type in ('TABLE', 'SEQUENCE')"
                            "  and object_name %s like 'X%%'" % negate)
    for type, old_name in c:
      new_name = rename(old_name)
      rows.append("Renaming %s %s to %s" % (type, old_name, new_name))
      self.api.execute("rename %s to %s" % (old_name, new_name))

    # Rename constraints.
    c, _ = self.api.execute("select constraint_name, table_name "
                            "from user_constraints "
		            "where constraint_name %s like 'X%%' "
			    "  and constraint_name not like 'SYS%%'" % negate)
    for old_name, table_name in c:
      new_name = rename(old_name)
      rows.append("Renaming %s [%s] to %s" % (old_name, table_name, new_name))
      self.api.execute("alter table %s rename constraint %s to %s"
		       % (table_name, old_name, new_name))

    # Rename non-constraint indices.
    c, _ = self.api.execute("select index_name, table_name "
                            "from user_indexes "
		            "where index_name %s like 'X%%' "
			    "  and index_name not like 'SYS%%'" % negate)
    for old_name, table_name in c:
      new_name = rename(old_name)
      rows.append("Renaming index %s [%s] to %s" % (old_name, table_name, new_name))
      self.api.execute("alter index %s rename to %s" % (old_name, new_name))

    # Rename triggers.
    c, _ = self.api.execute("select trigger_name, table_name "
                            "from user_triggers "
		            "where trigger_name %s like 'X%%' "
			    "  and trigger_name not like 'SYS%%'" % negate)
    for old_name, table_name in c:
      new_name = rename(old_name)
      rows.append("Renaming trigger %s [%s] to %s" % (old_name, table_name, new_name))
      self.api.execute("alter trigger %s rename to %s" % (old_name, new_name))

    return rows

  @restcall
  def put(self):
    """Insert database schema.

    The database must be previously empty, either not have any schema at all,
    or have the existing schema moved out of the way with a POST. This must
    be executed for the master admin account. If the current database object
    has multiple accounts, automatically also installs grants for reader and
    writer accounts.

    The caller must have global admin privileges.

    :returns: a simple 'ok' object on success; if the schema contains roles,
              the 'ok' is preceded by dictionaries with role/password pairs."""
    rows = []
    for stmt in self._schema.split(";"):
      while stmt.upper().find("IDENTIFIED BY @PASSWORD@") >= 0:
        passwd = mkpasswd()
        rows.append({ stmt: passwd })
        stmt = stmt.replace("@PASSWORD@", passwd, 1)
      self.api.execute(stmt)

    # Get all objects requiring grants, existing roles (created above),
    # and possible foo_reader/foo_writer accounts for current account.
    c, _ = self.api.execute("select object_name from user_objects"
                            " where object_type in ('TABLE', 'SEQUENCE')")
    objs = [o for o, in c]

    c, _ = self.api.execute("select granted_role from user_role_privs"
                            " where admin_option = 'YES'")
    roles = [r for r, in c]

    c, _ = self.api.execute("select username from all_users"
		            " where username = sys_context('userenv', 'session_user') || '_READER'"
			    "    or username = sys_context('userenv', 'session_user') || '_WRITER'")
    accts = [a for a, in c]
    reader = [a for a in accts if a.endswith("_READER")]
    writer = [a for a in accts if a.endswith("_WRITER")]

    # Grant all roles to the writer account, if any.
    if writer:
      for role in roles:
        self.api.execute("grant %s to %s" % (role, writer[0]))

    # Revoke all grants on all objects, then grant read access to the
    # reader and writer accounts, and update rights to specific roles
    # to be used inside the writer account. The current account keeps
    # all privileges on everything.
    for obj in objs:
      for role in reader + writer + roles:
        self.api.execute("revoke all on %s from %s" % (obj, role))
      for role in reader + writer:
        self.api.execute("grant select on %s to %s" % (obj, role))
      if writer:
        for role in roles:
	  if role == "SITEDB_WEBSITE":
	    if obj.startswith('TIER') or obj.startswith('CRYPT') or obj.startswith('CONTACT'):
              pass
	    elif obj.startswith('RESOURCE_PLEDGE') or obj.startswith('RESOURCE_DELIVERED'):
              self.api.execute("grant insert, select on %s to %s" % (obj, role))
	    else:
              self.api.execute("grant delete, insert, select, update on %s to %s" % (obj, role))

    rows.append('ok')
    return rows

  @restcall
  def delete(self, action):
    """Delete database schema, either all of it, or the current one, or
    a previously archived schema.

    The database must contain a schema previously intialised with PUT.
    The operation removes all tables, sequences, indices and constraints
    by truly deleting them, unlike POST which just archives them. The
    possible actions are ``all`` to delete everything, ``current`` to
    delete the current production schema but leave archived one in place,
    or ``archive`` to delete archived schema (objects with prefix ``X``)
    and leave current production schema alone.

    The caller must have global admin privileges.

    :arg str action: delete action to perform.
    :returns: a simple 'ok' object on success."""
    some_objs = ['SEQUENCE', 'MATERIALIZED VIEW', 'VIEW', 'TABLE',
		 'INDEX', 'SYNONYM', 'TRIGGER']
    more_objs = ['FUNCTION', 'PROCEDURE', 'PACKAGE', 'PACKAGE BODY']
    if action == 'all':
      condition = " where object_type in (%s)" % \
        ", ".join(["'%s'" % x for x in some_objs + more_objs])
    elif action == 'current' or action == 'archive':
      negation = (action == 'current' and 'not') or ''
      condition = " where object_type in (%s) and object_name %s like 'X%%'" % \
        (", ".join(["'%s'" % x for x in some_objs]), negation)
    else:
      raise RuntimeError("Internal error, invalid 'action'")

    rows = []
    for type in types:
      c, _ = self.api.execute("select object_type, object_name"
                              " from user_objects%s" % condition)
      for type, name in c:
        rows.append("Dropping %s %s" % (type, name))
	cascade = (type == 'TABLE' and ' cascade constraints') or ''
        self.api.execute("drop %s %s%s" % (type, name, cascade))

    if action == 'all':
      c, _ = self.api.execute("select granted_role from user_role_privs"
			      " where admin_option = 'YES'")
      for name, in c:
        rows.append("Dropping ROLE %s" % name)
        self.api.execute("drop role %s" % name)

    return rows
