import re

#: Regular expression for CMSSW architecture.
RX_ARCH      = re.compile(r"^[a-z0-9]+(_[a-z0-9]+){2}$")

#: Regular expression for CMSSW releases.
RX_RELEASE   = re.compile(r"^CMSSW(_[A-Za-z0-9_]+){3,}$")

#: Regular expression for labels: groups, roles, etc.
RX_LABEL     = re.compile(r"^[-A-Za-z0-9 _]+$")

#: Regular expression for site names.
RX_SITE      = RX_LABEL

#: Regular expression for site CMS names.
RX_CMS_NAME  = re.compile(r"^T\d+_[A-Z]{2}_[A-Za-z0-9_]+$")

#: Regular expression for tier names.
RX_TIER      = re.compile(r"^Tier \d+$")

#: Regular expression for user/login names.
RX_USER      = re.compile(r"^[a-z0-9_]+$")

#: Regular expression for passwords.
RX_PASSWD    = re.compile(r"^([*]|(RemovedUser--)?[A-Za-z0-9._/]{13,})$")

#: Regular expression for human names.
RX_NAME      = re.compile(r"^((?iu)[-\w ]*)$")

#: Regular expression for country names.
RX_COUNTRY   = re.compile(r"^((?iu)[-\w, ]*)$")

#: Regular expression for site usage (= grid middleware).
RX_USAGE     = re.compile(r"^(LCG|OSG|ARC|other)$")

#: Regular expression for yes/no setting.
RX_YES_NO    = re.compile(r"^[yn]$")

#: Regular expression for X509 DNs.
RX_DN        = re.compile(r"^(/[A-Z]+=((?iu)[-\w _@]+))*$", re.I)

#: Regular expression for e-mail addresses.
RX_EMAIL     = re.compile(r"^([-A-Z0-9_.%+]+@([-A-Z0-9]+\.)+[A-Z]{2,4})?$", re.I)

#: Regular expression for phone numbers.
RX_PHONE     = re.compile(r"^(\+[0-9]+)?([- .][0-9]+)*$")

#: Regular expression for IM handles.
RX_IM        = re.compile(r"^([-A-Z0-9_.%+]+(@([-A-Z0-9]+\.)+[A-Z]{2,4})?)?$", re.I)

#: Regular expression for possible name alias types.
RX_NAME_TYPE = re.compile(r"^(lcg|cms|phedex)$")

#: Regular expression for possible resource types.
RX_RES_TYPE  = re.compile(r"^(SE|CE)$")

#: Regular expression for fully qualified domain names.
RX_FQDN      = re.compile(r"^(([-A-Z0-9]+\.)+[A-Z]{2,4})?$", re.I)

#: Regular expression for URLs.
RX_URL       = re.compile(r"^(https?://([-A-Z0-9]+\.)+[A-Z]{2,4}(:\d+)?(/[-A-Z0-9_.%/+]*)?)?$", re.I)
