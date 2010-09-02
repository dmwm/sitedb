/**
 *
 *  "Site" definition tables
 *
 **/

/**
 * Table describing a site
 **/
create table t_v2_site (
  id number(10) not null,
  cms_name varchar(100) not null,
  second_name varchar(100) not null,
  country varchar(100) not null,
  usage varchar(100),
  url varchar(1000),
  logourl varchar(1000),
  getdevlrelease char(1),
  manualinstall char(1),
  -- Probably going to need lots of othr ID's (SAM, Dashboard etc) so 
  -- maybe need a table for that, instead of making this one huge!
  --
  constraint pk_v2_site primary key (id),
  constraint uk_v2_site unique (cms_name),
  
  constraint check_cms_name_is_valid check (regexp_like(cms_name, 
  ^T[0-3%]((_[A-Z]{2}(_[A-Za-z]+)*)?)$))
  
);
create s_v2_site increment by 1 start with 1;
create index i_v2_site_tier on site (tier);

/**
 * A site has a name to identify it with SAM/WLCG. A site (TN_XX_ABC) can have
 * many SAM names, and a SAM name can be used for more than one site (e.g. CERN)
 **/
create table t_v2_sam_name (
  id      number(10) not null,
  name    varchar(100) not null,
  site    number(10) not null,
  constraint pk_v2_samid primary key (id),
  constraint uk_v2_samname_site unique (name, site)
  constraint fk_v2_sam_site_association
    foreign key (site) references t_v2_site (id)
    on delete cascade
);
create sequence s_v2_sam_name increment by 1 start with 1;

/**
 * Site's official resource pledge 
 **/
create table t_v2_resource_pledge (
  pledgeid              number(10) not null,
  site          number(10) not null,
  pledgedate      timestamp not null,
  pledgequarter     float,
  cpu         float,
  job_slots       float,  
  disk_store      float,
  tape_store      float,
  wan_store       float,
  local_store     float,
  national_bandwidth  float,
  opn_bandwidth     float,
  status        char(1),
  --
  constraint pk_v2_resource_pledge primary key (pledgeid),
  constraint fk_v2_resource_pledge_site
    foreign key (site) references t_v2_site (id)
    on delete cascade
);
create sequence s_v2_resource_pledge increment by 1 start with 1;

/*
 * Site's resource element (CE, SE, Squids etc.)
 */
create table t_v2_resource_element (
  id      number(10) not null,
  site      number(10) not null,
  fqdn      varchar(200),
  type      varchar(100),
  is_primary    char(1),
  --
  constraint pk_v2_resource_element primary key (id),
  constraint fk_v2_resource_element_site
    foreign key (site) references t_v2_site (id)
    on delete cascade
);
create sequence s_v2_resource_element increment by 1 start with 1;
create index i_v2_resource_element_site on resource_element (site);

/* Table for tracking pinned software releases */
create table t_v2_pinned_releases (
  ce_id     number(10) not null,
  release   varchar(100),
  arch      varchar(100),
  --
  constraint fk_v2_pin_resource_element
    foreign key (ce_id) references t_v2_resource_element (id)
    on delete cascade
);


/**
 *
 *  Security Module tables
 *
 **/

/* List of cryptographic keys for the security module */
create table t_v2_crypt_key (
  id      number(10) not null,
  cryptkey    varchar(80) not null,
  time      timestamp,
  --
  constraint pk_v2_crypt_key primary key (id)
);
create sequence s_v2_crypt_key increment by 1 start with 1;
create index i_v2_crypt_key_cryptkey on crypt_key (cryptkey);
create index i_v2_crypt_key_time on crypt_key (time);

/*
 * List of usernames and passwords for the secuirty module 
 */
create table t_v2_user_passwd (
  username    varchar(60) not null,
  passwd    varchar(30) not null,
  --
  constraint pk_v2_user_passwd primary key (username)
);
create index i_v2_user_passwd_passwd on user_passwd (passwd);


/**
 *
 *  "Person" definition tables
 * 
 **/

/*
 * A human being, in most cases
 */
create table t_v2_contact (
  id      number(10) not null,
  surname   varchar(1000) not null,
  forename    varchar(1000) not null,
  email     varchar(1000) not null,
  username    varchar(60),
  dn      varchar(1000),
  phone1    varchar(100),
  phone2    varchar(100),
  im_handle   varchar(100),
  --
  constraint pk_v2_contact primary key (id),
  constraint uk_v2_contact_dn unique (dn),
  constraint uk_v2_contact_username unique (username),
  constraint fk_v2_contact_username
    foreign key (username) references t_v2_user_passwd (username)
    on delete set null
  constraint check_email_is_valid check (regexp_like(email,
'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$'))

);
create sequence s_v2_contact increment by 1 start with 1;
create index i_v2_contact_surname on contact (surname);
create index i_v2_contact_forename on contact (forename);


/*
 * Management roles for a site/group e.g. 'PhedexSiteAdmin', 'PhedexDataManager' 
 */
create table t_v2_role (
  id      number(10) not null,
  title     varchar(100) not null,
  --
  constraint pk_v2_role primary key (id),
  constraint uk_v2_role_title unique (title)
);
create sequence s_v2_role increment by 1 start with 1;

/* 
 * An abstract group humans can belong to e.g. 'higgs','top','BSM','global' etc.
 * Groups have a type - comp, dpg, pag, pog and an optional contact (e.g. an 
 * email or a hypernews address)
*/
create table t_v2_user_group (
  id      number(10) not null,
  name      varchar(100) not null,
  group_type  varchar(100) not null default 'comp',
  contact     varchar(100),
  --
  constraint pk_v2_user_group primary key (id), 
  constraint uk_v2_user_group_name unique (name)
);
create sequence s_v2_user_group increment by 1 start with 1;

/*
 * A group is associated to one or more sites
 */
create table t_v2_site_group_association (
  site      number(10) not null,
  user_group  number(10) not null,
  --
  -- only associate a site to a group once
  constraint uk_v2_site_group_association unique (site, user_group),
  constraint fk_v2_site_group_association_site
    foreign key (site) references t_v2_site (id)
    on delete cascade,
  constraint fk_v2_site_group_association_group
    foreign key (user_group) references t_v2_user_group (id)
    on delete cascade
);

/* 
 * A mapping of humans to responsibilites associated with a site e.g. "Bob is 
 * the PhedexSiteAdmin of T4_AN_Antartica" 
 */
create table t_v2_site_responsibility (
  contact   number(10) not null,
  role      number(10) not null,
  site      number(10) not null,
  --
  constraint pk_v2_site_resp primary key (contact, role, site),
  constraint fk_v2_site_resp_contact
    foreign key (contact) references t_v2_contact (id)
    on delete cascade,
  constraint fk_v2_site_resp_role
    foreign key (role) references t_v2_role (id)
    on delete cascade,
  constraint fk_v2_site_resp_site
    foreign key (site) references t_v2_site (id)
    on delete cascade
);
create index i_v2_site_resp_role on site_responsibility (role);
create index i_v2_site_resp_site on site_responsibility (site);

/* 
 * A mapping of humans to responsibilities associated with a group e.g. "Joe is
 * the ProdRequestManager of the Gravitino group 
 */
create table t_v2_group_responsibility (
  contact   number(10) not null,
  role      number(10) not null,
  user_group    number(10) not null,
  --
  constraint pk_v2_group_resp_contact primary key (contact, role, user_group),
  constraint fk_v2_group_resp_contact
    foreign key (contact) references t_v2_contact (id)
    on delete cascade,
  constraint fk_v2_group_resp_role
    foreign key (role) references t_v2_role (id)
    on delete cascade,
  constraint fk_v2_group_resp_user_group
    foreign key (user_group) references t_v2_user_group (id)
    on delete cascade
);
create index i_v2_group_resp_role on group_responsibility (role);
create index i_v2_group_resp_user_group on group_responsibility (user_group);