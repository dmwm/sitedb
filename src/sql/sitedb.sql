create table tier (
  id			number(10) not null,
  pos			number(10) not null,
  name			varchar(100) not null,
  constraint pk_tier primary key (id),
  constraint uk_tier_pos unique (pos),
  constraint uk_tier_name unique (name)
);
create sequence tier_sq increment by 1 start with 1;

create table site (
  id			number(10) not null,
  name			varchar(100) not null,
  -- cms_name		varchar(100) not null,
  tier			number(10) not null,
  country		varchar(100) not null,
  usage			varchar(100),
  url			varchar(1000),
  logourl		varchar(1000),
  getdevlrelease	char(1),
  manualinstall		char(1),
  constraint pk_site primary key (id),
  constraint uk_site unique (name),
  constraint fk_site_tier foreign key (tier) references tier (id)
);
create sequence site_sq increment by 1 start with 1;
create index ix_site_tier on site (tier);

create table site_association (
  parent_site		number(10) not null,
  child_site		number(10) not null,
  constraint pk_site_association primary key (parent_site, child_site),
  constraint fk_site_association_parent
    foreign key (parent_site) references site (id)
    on delete cascade,
  constraint fk_site_association_child
    foreign key (child_site) references site (id)
    on delete cascade
);
create index ix_site_association_child on site_association (child_site);

create table resource_pledge (
  pledgeid              number(10) not null,
  site			number(10) not null,
  pledgedate		timestamp not null,
  pledgequarter		number(4),
  cpu			float,
  job_slots		float,
  disk_store		float,
  tape_store		float,
  wan_store		float,
  local_store		float,
  national_bandwidth	float,
  opn_bandwidth		float,
  status		char(1),
  constraint pk_resource_pledge primary key (pledgeid),
  constraint fk_resource_pledge_site
    foreign key (site) references site (id)
    on delete cascade
);
create sequence resource_pledge_sq increment by 1 start with 1;

-- Site's official resource pledge
create table resource_delivered (
  deliveryid            number(10) not null,
  site			number(10) not null,
  deliverydate		timestamp not null,
  pledgequarter		float,
  cpu			float,
  job_slots		float,
  disk_store		float,
  tape_store		float,
  wan_store		float,
  local_store		float,
  national_bandwidth	float,
  opn_bandwidth		float,
  constraint pk_resource_delivered primary key (deliveryid),
  constraint fk_resource_delivered_site
    foreign key (site) references site (id)
    on delete cascade
);
create sequence resource_delivered_sq increment by 1 start with 1;

-- Site's resource element (disks, storage)
create table resource_element (
  id			number(10) not null,
  site			number(10) not null,
  fqdn			varchar(200),
  type			varchar(100),
  is_primary		char(1),
  constraint pk_resource_element primary key (id),
  constraint fk_resource_element_site
    foreign key (site) references site (id)
    on delete cascade
);
create sequence resource_element_sq increment by 1 start with 1;
create index ix_resource_element_site on resource_element (site);

-- Table for tracking pinned software releases
create table pinned_releases (
  ce_id			number(10) not null,
  release		varchar(100),
  arch			varchar(100),
  --
  constraint fk_pin_resource_element
    foreign key (ce_id) references resource_element (id)
    on delete cascade
);

-- Site's phedex nodes
create table phedex_node (
  id			number(10) not null,
  site			number(10) not null,
  name			varchar(100) not null,
  --
  constraint pk_phedex_node primary key (id),
  constraint uk_phedex_node_name unique (id, name),
  constraint fk_phedex_node_site
    foreign key (site) references site (id)
  on delete cascade
    -- cascade?  depends on how dependant phedex becomes on this...
);
create sequence phedex_node_sq increment by 1 start with 1;
create index ix_phedex_node_site on phedex_node (site);
create index ix_phedex_node_name on phedex_node (name);

-- Site's psn nodes
create table psn_node (
  id                    number(10) not null,
  site                  number(10) not null,
  name                  varchar(100) not null,
  --
  constraint pk_psn_node primary key (id),
  constraint uk_psn_node_name unique (name) using index (create index ix_psn_node_name on psn_node (name)),
  constraint fk_psn_node_site
    foreign key (site) references site (id)
  on delete cascade
    -- cascade?  depends on how dependant psn becomes on this...
);
create sequence psn_node_sq increment by 1 start with 1;
create index ix_psn_node_site on psn_node (site);

----
--   Site performance tables
----

-- High-level statistics about a site's performance
create table performance (
  site			number(10) not null,
  time			timestamp not null,
  job_quality		float,
  transfer_quality	float,
  jobrobot_quality	float,
  job_io		float,
  wan_io		float,
  phedex_io		float,
  phedex_sum_tx_in	float,
  phedex_sum_tx_out	float,
  --
  constraint pk_performance primary key (site, time),
  constraint fk_performance_site
    foreign key (site) references site (id)
    on delete cascade
);



-- High-level statistics about a sites job activity
create table job_activity (
  site			number(10) not null,
  time			timestamp not null,
  activity		varchar(100),
  num_jobs		number(10),
  --
  constraint pk_job_activity primary key (site, time),
  constraint fk_job_activity_site
    foreign key (site) references site (id)
    on delete cascade
);



----
--  Security Module tables
----

-- List of cryptographic keys for the security module
create table crypt_key (
  id			number(10) not null,
  cryptkey		varchar(80) not null,
  time			timestamp,
  --
  constraint pk_crypt_key primary key (id)
);
create sequence crypt_key_sq increment by 1 start with 1;
create index ix_crypt_key_cryptkey on crypt_key (cryptkey);
create index ix_crypt_key_time on crypt_key (time);



-- List of usernames and passwords for the secuirty module
CREATE TABLE user_passwd (
  username		varchar(60) not null,
  passwd		varchar(30) not null,
  --
  constraint pk_user_passwd primary key (username)
);
create index ix_user_passwd_passwd on user_passwd (passwd);



----
--  "Person" definition tables
----

-- A human being
create table contact (
  id			number(10) not null,
  surname		varchar(1000) not null,
  forename		varchar(1000) not null,
  email			varchar(1000) not null,
  username		varchar(60),
  dn			varchar(1000),
  phone1		varchar(100),
  phone2		varchar(100),
  im_handle		varchar(100),
  --
  constraint pk_contact primary key (id),
  constraint uk_contact_dn unique (dn),
  constraint uk_contact_username unique (username),
  constraint fk_contact_username
    foreign key (username) references user_passwd (username)
    on delete set null
);
create sequence contact_sq increment by 1 start with 1;
create index ix_contact_surname on contact (surname);
create index ix_contact_forename on contact (forename);




-- Management roles e.g. 'PhedexSiteAdmin', 'PhedexDataManager'
create table role (
  id			number(10) not null,
  title			varchar(100) not null,
  description           varchar(4000), 
  --
  constraint pk_role primary key (id),
  constraint uk_role_title unique (title)
);
create sequence role_sq increment by 1 start with 1;



-- An abstract group humans can belong to e.g. 'higgs','top','BSM','global' etc.
create table user_group (
  id			number(10) not null,
  name			varchar(100) not null,
  --
  constraint pk_user_group primary key (id),
  constraint uk_user_group_name unique (name)
);
create sequence user_group_sq increment by 1 start with 1;



-- A mapping of humans to responsibilites associated with a site
-- e.g. "Bob is the PhedexSiteAdmin of T4_Antartica"
create table site_responsibility (
  contact		number(10) not null,
  role			number(10) not null,
  site			number(10) not null,
  --
  constraint pk_site_resp primary key (contact, role, site),
  constraint fk_site_resp_contact
    foreign key (contact) references contact (id)
    on delete cascade,
  constraint fk_site_resp_role
    foreign key (role) references role (id)
    on delete cascade,
  constraint fk_site_resp_site
    foreign key (site) references site (id)
    on delete cascade
);
create index ix_site_resp_role on site_responsibility (role);
create index ix_site_resp_site on site_responsibility (site);



-- A mapping of humans to responsibilities associated with a group
-- e.g. "Joe is the ProdRequestManager of the Gravitino group
create table group_responsibility (
  contact		number(10) not null,
  role			number(10) not null,
  user_group		number(10) not null,
  --
  constraint pk_group_resp_contact primary key (contact, role, user_group),
  constraint fk_group_resp_contact
    foreign key (contact) references contact (id)
    on delete cascade,
  constraint fk_group_resp_role
    foreign key (role) references role (id)
    on delete cascade,
  constraint fk_group_resp_user_group
    foreign key (user_group) references user_group (id)
    on delete cascade
);
create index ix_group_resp_role on group_responsibility (role);
create index ix_group_resp_user_group on group_responsibility (user_group);



-- A mapping of humans to responsibilities associated with a PNN
-- e.g. "Joe is the Global Admin of the T2_CH_CERN
create table data_responsibility (
  contact               number(10) not null,
  role                  number(10) not null,
  pnn                   number(10) not null,
  --
  constraint pk_data_resp primary key (contact, role, pnn),
  constraint fk_data_resp_contact
    foreign key (contact) references contact (id)
    on delete cascade,
  constraint fk_data_resp_role
    foreign key (role) references role (id)
    on delete cascade,
  constraint fk_data_resp_pnn
    foreign key (pnn) references phedex_node (id)
    on delete cascade
);
create index ix_data_resp_role on data_responsibility (role);
create index ix_data_resp_pnn on data_responsibility (pnn);


----
--  Generic survey tables
----

-- Defines a survey and associates it with its creator
create table survey (
  id			number(10) not null,
  name			varchar(100) not null,
  creator		number(10),
  opened		timestamp,
  closed		timestamp,
  --
  constraint pk_survey primary key (id),
  constraint fk_survey_creator
    foreign key (creator) references contact (id)
    on delete set null
);
create sequence survey_sq increment by 1 start with 1;
create index ix_survery_creator on survey (creator);

create table survey_who (
  survey		number(10) not null,
  tier			number(10) not null,
  role			number(10) not null,
  --
  constraint fk_survey_who_survey
    foreign key (survey) references survey (id)
    on delete cascade,
  constraint fk_survey_who_tier
    foreign key (tier) references tier (id),
  constraint fk_survey_who_role
    foreign key (role) references role (id)
    on delete cascade
);
create index ix_survey_who_survey on survey_who (survey);
create index ix_survey_who_tier on survey_who (tier);
create index ix_survey_who_role on survey_who (role);


-- For sending out surveys by tier
create table survey_tiers (
  survey		number(10) not null,
  tier			number(10) not null,
  --
  constraint fk_survey_tiers_survey
    foreign key (survey) references survey (id)
    on delete cascade,
  constraint fk_survey_tiers_tier
    foreign key (tier) references tier (id)
    -- we don't delete tiers
);
create index ix_survey_tiers_survey on survey_tiers (survey);
create index ix_survey_tiers_tier on survey_tiers (tier);



-- For sending out surveys by role
create table survey_roles (
  survey		number(10) not null,
  role			number(10) not null,
  --
  constraint fk_survey_roles_survey
    foreign key (survey) references survey (id)
    on delete cascade,
  constraint fk_survey_roles_role
    foreign key (role) references role (id)
    on delete cascade
);
create index ix_survey_roles_survey on survey_roles (survey);
create index ix_survey_roles_role on survey_roles (role);



-- A question on a survey
create table question (
  id			number(10) not null,
  survey		number(10) not null,
  question		varchar(4000) not null,
  form_type		varchar(100) not null,
  --
  constraint pk_question primary key (id),
  constraint fk_question_survey
    foreign key (survey) references survey (id)
    on delete cascade
);
create sequence question_sq increment by 1 start with 1;
create index ix_question_survey on question (survey);



-- A default answer on a survey (for checkbox or drop-down menu style questions)
create table question_default (
  question		number(10) not null,
  pos			number(10) not null,
  value			varchar(4000) not null,
  --
  constraint pk_question_default primary key (question, pos),
  constraint fk_question_default_question
    foreign key (question) references question (id)
    on delete cascade
);



-- A site's answer to the survey question
create table question_answer (
  site			number(10) not null,
  question		number(10) not null,
  answer		varchar(4000) not null,
  --
  constraint pk_question_answer primary key (site, question),
  constraint fk_question_answer_site
    foreign key (site) references site (id)
    on delete cascade,
  constraint fk_question_answer_question
    foreign key (question) references question (id)
    on delete cascade
);
create index ix_question_answer_question on question_answer (question);

----
-- Tables to support naming convention
----

create table cms_name(
  id			number(10) not null,
  name			varchar(100) not null,
  constraint pk_cms_name primary key (id),
  constraint uk_cms_name unique (name)
);
create sequence cms_name_sq increment by 1 start with 1;

create table sam_name (
  id			number(10) not null,
  name			varchar(100) not null,
  gocdbid		number(10),
  constraint pk_sam_name primary key (id),
  constraint uk_sam_name unique (name)
);
create sequence sam_name_sq increment by 1 start with 1;

create table site_cms_name_map(
  site_id			number(10) not null,
  cms_name_id			number(10) not null,
  constraint fk_naming_site_cms_id
    foreign key (cms_name_id) references cms_name (id)
    on delete cascade,
  constraint fk_naming_site_id
    foreign key (site_id) references site (id)
    on delete cascade
);

create table phedex_node_cms_name_map(
  node_id				number(10) not null,
  cms_name_id			number(10) not null,
  constraint fk_naming_node_cms_id
    foreign key (cms_name_id) references cms_name (id)
    on delete cascade,
  constraint fk_naming_node_id
    foreign key (node_id) references phedex_node (id)
    on delete cascade
);

create table psn_node_phedex_name_map(
  phedex_id                               number(10) not null,
  psn_id                   number(10) not null,
  constraint fk_psn_node_phedex_id
    foreign key (phedex_id) references phedex_node (id)
    on delete cascade,
  constraint fk_psn_node_id
    foreign key (psn_id) references psn_node (id)
    on delete cascade,
  constraint uk_psn_id unique (phedex_id, psn_id)
);

create table resource_cms_name_map(
  resource_id			number(10) not null,
  cms_name_id			number(10) not null,
  constraint fk_naming_resource_cms_id
    foreign key (cms_name_id) references cms_name (id)
    on delete cascade,
  constraint fk_naming_resource_id
    foreign key (resource_id) references resource_element (id)
    on delete cascade
);

create table sam_cms_name_map(
  sam_id			number(10) not null,
  cms_name_id			number(10) not null,
  constraint fk_naming_sam_cms_id
    foreign key (cms_name_id) references cms_name (id)
    on delete cascade,
  constraint fk_naming_sam_id
    foreign key (sam_id) references sam_name (id)
    on delete cascade
);

---- 
--  Tables for Federations Pledges
----

create table sites_federations_names_map(
  id 				number(10) not null,
  site_id 			number(10) not null,
  federations_names_id		number(10) not null,
  constraint pk_sites_federations_names_map primary key (id),
  constraint uq_sites_fed_names_map unique (site_id)
);
create sequence sites_federations_names_map_sq by 1 start with 1;

create table federations_pledges(
  id 				number(10) not null,
  federations_names_id		number(10) not null,
  year				number(10) not null,
  cpu				float,
  disk				float,
  tape				float,
  feddate			timestamp not null,
  constraint pk_federations_pledges primary key(id)
);
create sequence federations_pledges_sq by 1 start with 1;

create table all_federations_names(
  id 				number(10) not null,
  name				varchar(10) not null,
  country			varchar(10) not null,
  constraint pk_all_federations_names primary key(id),
  constraint uq_all_fed_names unique (name)
);
create sequence all_federations_names_sq by 1 start with 1;

----
--  Tables for ESP credits
----

create table sites_esp_credits(
  id				number(10) not null,
  site				number(10) not null,
  year				number(4) not null,
  esp_credit			float not null,
  constraint pk_sites_esp_credits primary key (id)
);
create sequence sites_esp_credits_sq by 1 start with 1;

-- begin execute immediate 'create role sitedb_website', exception when others then if sqlcode = -01921 then null, else raise, end if, end
create role sitedb_website identified by @PASSWORD@;
