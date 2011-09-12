insert into role (id, title) values (role_sq.nextval, 'Global Admin');
insert into user_group (id, name) values (user_group_sq.nextval, 'global');
insert into tier (id, pos, name) values (tier_sq.nextval, 0, 'Tier 0');
insert into tier (id, pos, name) values (tier_sq.nextval, 1, 'Tier 1');
insert into tier (id, pos, name) values (tier_sq.nextval, 2, 'Tier 2');
insert into tier (id, pos, name) values (tier_sq.nextval, 3, 'Tier 3');

insert into user_passwd (username, passwd) values ('metson', '*');
insert into user_passwd (username, passwd) values ('lat', '*');
insert into user_passwd (username, passwd) values ('pkreuzer', '*');
insert into user_passwd (username, passwd) values ('rossman', '*');

insert into contact (id, email, forename, surname, dn, username, phone1, phone2, im_handle)
  values (contact_sq.nextval, 'simon.metson@cern.ch', 'Simon', 'Metson',
          '/C=UK/O=eScience/OU=Bristol/L=IS/CN=simon metson',
          'metson', null, null, null);
insert into contact (id, email, forename, surname, dn, username, phone1, phone2, im_handle)
  values (contact_sq.nextval, 'lat@cern.ch', 'Lassi', 'Tuura',
          '/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=lat/CN=437145/CN=Lassi Tuura',
          'lat', null, null, null);
insert into contact (id, email, forename, surname, dn, username, phone1, phone2, im_handle)
  values (contact_sq.nextval, 'peter.kreuzer@cern.ch', 'Peter', 'Kreuzer',
          '/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=pkreuzer/CN=406463/CN=Peter Kreuzer',
          'pkreuzer', null, null, null);
insert into contact (id, email, forename, surname, dn, username, phone1, phone2, im_handle)
  values (contact_sq.nextval, 'rossman@fnal.gov', 'Paul', 'Rossman',
          '/DC=org/DC=doegrids/OU=People/CN=Paul Rossman 364403',
          'rossman', null, null, null);

insert into group_responsibility (contact, role, user_group)
  values ((select id from contact where email = 'simon.metson@cern.ch'),
          (select id from role where title = 'Global Admin'),
          (select id from user_group where name = 'global'));
insert into group_responsibility (contact, role, user_group)
  values ((select id from contact where email = 'lat@cern.ch'),
          (select id from role where title = 'Global Admin'),
          (select id from user_group where name = 'global'));
insert into group_responsibility (contact, role, user_group)
  values ((select id from contact where email = 'peter.kreuzer@cern.ch'),
          (select id from role where title = 'Global Admin'),
          (select id from user_group where name = 'global'));
insert into group_responsibility (contact, role, user_group)
  values ((select id from contact where email = 'rossman@fnal.gov'),
          (select id from role where title = 'Global Admin'),
          (select id from user_group where name = 'global'));
