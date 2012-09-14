import re

### IMPORTANT NOTE. ###################################################
### FrontPage automatically exports all the regexps here to javascript
### for input validation. The regexps must be compatible with XRegExp
### (cf. xregexp.com) with added [\w] -> [\p{L}\p{N}\p{Pc}\p{M}] mapping
### in unicode-compatible form, and (?u) flag is completely ignored.
### Apply all other flags using (?i) syntax in the regexp itself, any
### re.compile() options will be lost in the javascript export.

#: Regular expression for CMSSW architecture.
RX_ARCH      = re.compile(r"^[a-z0-9]+(_[a-z0-9]+){2}$")

#: Regular expression for CMSSW releases.
RX_RELEASE   = re.compile(r"^CMSSW(_[A-Za-z0-9_]+){3,}$")

#: Regular expression for labels: groups, roles, etc.
RX_LABEL     = re.compile(r"^[-A-Za-z0-9 _]+$")

#: Regular expression for quarters: YYYY.Q.
RX_QUARTER   = re.compile(r"^20(?:0[789]|1[0-9]|20)\.[1234]$")

#: Regular expression for site names.
RX_SITE      = RX_LABEL

#: Regular expression for site CMS names.
RX_CMS_NAME  = re.compile(r"^T\d+_[A-Z]{2}_[A-Za-z0-9_]+$")

#: Regular expression for tier names.
RX_TIER      = re.compile(r"^Tier \d+$")

#: Regular expression for user/login names.
RX_USER      = re.compile(r"^(?:[a-z0-9_]+(?:\.notcms|\.nocern)?"
                          r"|[a-z0-9]+@(?:[-a-z0-9]+\.)+[a-z]{2,5})$")

#: Regular expression for passwords.
RX_PASSWD    = re.compile(r"^([*]|(RemovedUser--)?[A-Za-z0-9._/]{13,})$")

#: Regular expression for passwords in clear.
RX_CPASSWD   = re.compile(r"^.{6,}$")

#: Regular expression for human names.
RX_NAME      = re.compile(r"(?iu)^([-\w '.]*)$")
RX_HN_NAME   = re.compile(r"(?iu)^([-\w '.(),\"]*)$")

#: Regular expression for country names.
RX_COUNTRY   = re.compile(r"(?iu)^([-\w, ']*)$")

#: Regular expression for site usage (= grid middleware).
RX_USAGE     = re.compile(r"^(LCG|OSG|ARC|other)$")

#: Regular expression for yes/no setting.
RX_YES_NO    = re.compile(r"^[yn]$")

#: Regular expression for X509 DNs.
RX_DN        = re.compile(r"(?iu)^(/[A-Z]+=([-\w _@'.()/]+))*$")

#: Regular expression for e-mail addresses.
RX_EMAIL     = re.compile(r"(?i)^[-A-Z0-9_.%+]+@([-A-Z0-9]+\.)+[A-Z]{2,5}$")

#: Regular expression for phone numbers.
RX_PHONE     = re.compile(r"^([0-9]{5,7}|\+[0-9]+([- .]?[0-9]+)*)?$")

#: Regular expression for IM handles.
RX_IM        = re.compile(r"(?i)^((aol|gtalk|msn|icq|jabber):[-A-Z0-9_.%+]+(@([-A-Z0-9]+\.)+[A-Z]{2,5})?)?$")

#: Regular expression for possible name alias types.
RX_NAME_TYPE = re.compile(r"^(lcg|cms|phedex)$")

#: Regular expression for possible resource types.
RX_RES_TYPE  = re.compile(r"^(SE|CE)$")

#: Regular expression for fully qualified domain names.
RX_FQDN      = re.compile(r"(?i)^(([-A-Z0-9]+\.)+[A-Z]{2,5})?$")

#: Regular expression for URLs.
RX_URL       = re.compile(r"(?i)^(https?://([-A-Z0-9]+\.)+[A-Z]{2,5}(:\d+)?(/[-A-Z0-9_.%/+]*)?)?$")
