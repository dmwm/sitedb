/**
 *  "Site" definition tables
 **/

/**
 * Table describing a site
 **/
create table t_site (
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
  constraint pk_site primary key (id),
  constraint uk_site unique (cms_name)
);
create sequence site_sq increment by 1 start with 1;
create index ix_site_tier on site (tier);

/**
 * insert into t_site (id, cms_name, second_name, country) values (1, 'T1_UK_RAL', 'RAL', 'UK');
**/