var Pledges = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;
  /** Dropdown button */
  var _showfedsites = null;

  /** Current state object, for event callbacks. */
  var _state = null;

  /** View master objects. */
  var _views = new ViewContentSet(Y, {
    main: "view-pledges-main",
    quarter: "view-pledges-quarter"
  });

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Pledges",
            ["whoami", "sites", "site-names",
             "site-associations", "resource-pledges", "federations-pledges",
             "federations-sites", "federations-pledges",
             "federations", "esp-credit"]);

  /** Utility function to format numbers prettily in given precision
      and with thousand separators. */
  var _shownum = function(n, prec)
  {
    if(n == 0 || n== null) return 0;
    return n ? X.thousands(sprintf("%." + prec + "f", n)) : "";
  };

  /** Utility function to format dates nicely for pledge tables. */
  var _pledgedate = function(date)
  {
    var t = new Date();
    t.setTime(date * 1000);
    return sprintf("%d %s %d", t.getDate(), X.MONTH[t.getMonth()], t.getFullYear());
  };

  /** Action handler for adding a pledge update. */
  var _addPledge = function(state, site, quarter, cpu,
                            tape, disk, local)
  {
    var obj = (site in state.sitesByCMS && state.sitesByCMS[site]);
    if (obj)
      state.modify([{
        method: "PUT", entity: "resource-pledges",
        data: { "site_name": obj.site_name, "quarter": quarter,
                "cpu": cpu, "disk_store": disk, "tape_store": tape,
                "local_store": local},
        message: "Updating pledge for " + Y.Escape.html(obj.canonical_name)
      }]);
  };

  /** Action handler for show/hide federation sites after click */
  var _showSites = function(name)
  {
    var x = X.findEventAncestor(name, "x-name");
    if (x)
    {
      var ele = document.getElementsByClassName(x.value);
      for (var i = 0; i< ele.length; i++)
      {
        if (ele[i].style.display == 'table-row')
        {
          ele[i].style.display = 'none';
        }
        else
        {
          ele[i].style.display = 'table-row';
          if ((i+1) == ele.length)
          {
            ele[i].style.borderBottom = '1px solid black';
          }
        }
      }
    }
  };

  /** Action handler for show/hide pledge history after click */
  var _showPledgesHistory = function(name)
  {
    var x = X.findEventAncestor(name, "x-name");
    if (x)
    {
      var ele = document.getElementsByClassName(x.value);
      for (var i = 0; i< ele.length; i++)
      {
        if (ele[i].style.display == 'table-row')
        {
          ele[i].style.display = 'none';
        }
        else
        {
          ele[i].style.display = 'table-row';
        }
      }
    }
  };

  /** View attach handler: delegate click buttons on this page. */
  this.attach = function()
   {
     _showfedsites = _self.doc.delegate("click", _showSites, ".showfedsites");
     _showpledhist = _self.doc.delegate("click", _showPledgesHistory, ".showpledgehistory");
   }

  /** Detach this view. Detaches view contents. */
  this.detach = function()
  {
    _showfedsites.detach();
    if(_showpledhist) _showpledhist.detach();
    _views.detach();
  };

  /** The main view page, show pledges by quarter, country and region. */
  this.main = function(req)
  {
    var content;
    var now = new Date();
    var curyear = now.getFullYear();
    var quarters = {}, vquarter = req.query.q || "";
    var cclist = {}, cc = req.query.c || "";
    var roots = {}, root = (req.query.r || "").toUpperCase();
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _state = state;
    var url = REST_SERVER_ROOT + "/" + X.encodeAsPath(instance) + "/pledges";
    _self.title(state, "Pledges");
    _self.loading(state);
    var federations = state.federationsSitesById;
    var federationsnames = state.federationsBYID;
    var federationspledges = state.federationsPledges;
    var espcredits = state.espcredit;
    var earlier = [];
    var quarter;
    var isgadmin = state.isGlobalAdmin();
    var qyear, qpart;
    var qmatch = vquarter && vquarter.match(/^(20(?:0[789]|1[0-9]|20))$/);
    var isadmin = state.isGlobalAdmin();
    if (! qmatch)
    {
      qyear = curyear;
    }
    else
    {
      qyear = qmatch[1];
    }

    var view = _views.attach("main", _self.doc);
    view.content("title", Y.Escape.html(qyear) + " resource pledges"
                 + (cc ? " for country " + Y.Escape.html(cc.toUpperCase()) : "")
                 + (root ? " for group " + Y.Escape.html(root.toUpperCase()) : ""));

    // Gather all quarters, countries and T1 group roots.
    Y.each(state.sitesByCMS, function(s) {
      Y.each(Object.keys(s.resource_pledges), function(q) { quarters[q] = 1; });
      cclist[s.cc] = 1;
      var p = s;
      while (p.tier_level > 1 && p.parent_site)
        p = p.parent_site;

      if (p.tier_level <= 1)
      {
        var stem = p.canonical_name
                   .replace(/^T\d+_[A-Z]+_([A-Za-z0-9]+)(_.*)?$/, "$1");
        if (! (stem in roots))
	  roots[stem] = { name: stem, root: p, sites: [] };
        roots[stem].sites.push(s);
        s.pledge_root = roots[stem];
      }
    });

    content = "";
    for (var year = curyear + 3; year >= Math.min(curyear - 4, 2007); --year)
    {
      content += "<div style='display:inline-block;width:6em;"
        + "border:1px solid #ddd;border-collapse:collapse"
        + (year == qyear ? ";background-color:#f0f0f0;font-face:bold" : "") + "'>"
        + "<span style='display:inline-block;width:100%;margin:auto;"
        + "text-align:center;border-bottom:1px dotted #ddd'>"
        + "<a class='internal' href='" + url + "?q=" + year + "'>"
	+	year + "</a></span><br />";
      content += "</div>";
    }
      earlier.push([qyear, qyear]);
    view.content("by-quarter", content);

    content = "<a style='padding-left:.5em' class='internal' href='"
              + url + "?q=" + vquarter + "'>All</a> -";
    Y.each(Object.keys(cclist).sort(d3.ascending), function(c) {
      var current = (cc && cc == c);
      content += (current ? "<b>" : "")
        + "<a style='padding-left:.5em' class='internal' href='"
        + url + "?q=" + vquarter + "&c=" + c + "'>" + c.toUpperCase()
        + "</a>" + (current ? "</b>" : "");
    });
    view.content("by-country", content);

    content = "<a style='padding-left:.5em' class='internal' href='"
              + url + "?q=" + vquarter + "'>All</a> -";
    Y.each(Object.keys(roots).sort(d3.ascending), function(r) {
      var current = (root && root == r);
      content += (current ? "<b>" : "")
        + "<a style='padding-left:.5em' class='internal' href='"
        + url + "?q=" + vquarter + "&r=" + r.toLowerCase() + "'>"
        + r + "</a>" + (current ? "</b>" : "");
    });
    view.content("by-tier1", content);

    var summary = { npledged: 0, cpu: 0, local_store: 0, tape_store: 0,
                    disk_store :0};
    var head = "</th><th>";
    var cell = "</td><td>";
    var faded = " style='color:#666;background-color:#f0f0f0'";
    content = "<thead><tr><th class='left' rowspan='2'>Country</th><th class='left' rowspan='2'>Site</th>"
      + "<th rowspan='2' title='Total processing power available to CMS'>"
      + "CPU<br />[KHS06]</th>"
      + "<th colspan='3' class='middle' title='Total storage allocated to"
      + " CMS'>Storage [TB]</th><th rowspan='2'>ESP credit</th>"
      + "</tr><tr><th>Tape</th><th>Disk</th><th>Local</th>"
      + "</tr></thead>";
    Y.each(Object.keys(state.sitesByTier).sort(d3.ascending), function(t) {
      var sites = [], pledged = {};var sitesfed = {};
      var total = { npledged: 0, cpu: 0, local_store: 0,
                    tape_store: 0, disk_store: 0};
    Y.each(state.sitesByTier[t], function(s) {
        if ((! cc && ! root)
            || (cc && s.cc == cc)
            || (root && s.pledge_root && s.pledge_root.name == root))
        {
          sites.push(s);
	  for (var i = 0; i < earlier.length; ++i)
          {
            var qkey = earlier[i][0];
            if (qkey in s.resource_pledges)
            {
              ++summary.npledged;
	      ++total.npledged;
	      pledged[s.canonical_name] = earlier[i];
              Y.each(s.resource_pledges[qkey], function(v, k) {
                total[k] += v;
                summary[k] += v;
              });
              break;
            }
          }
        }
      });
    Y.each(sites, function(s) {
      if (s.id in federations)
      {
        var fedID = federations[s.id]["fed_id"];
        if (fedID in federationsnames)
        {
          var temp = federationsnames[fedID].name;
          var temp_country = federationsnames[fedID].country;
          if (temp in sitesfed)
          {
            sitesfed[temp].sites.push(s);
          }
          else
          {
            sitesfed[temp] = Y.merge(sitesfed[temp],{sites : [s], fed_name : temp, country : temp_country});
          }
        }
        else
        {
          if ("No Federation" in sitesfed) sitesfed["No Federation"].sites.push(s);
          else sitesfed["No Federation"] = Y.merge(sitesfed["No Federation"], {sites : [s], fed_name : "No Federation", country : "zzz"});
        }
      }
      else
      {
        if("No Federation" in sitesfed) sitesfed["No Federation"].sites.push(s);
        else sitesfed["No Federation"] = Y.merge(sitesfed["No Federation"], {sites : [s], fed_name : "No Federation", country : "zzz"});
      }
    // fake country name to show not assigned sites to federation at the end
    });
      if (sites.length)
      {
        content += "<thead class='tier'><tr"
          + (total.npledged ? "" : faded)
          + ">"+ head +"<th class='left'>" + Y.Escape.html(t)
          + " (" + total.npledged + ")"
          + head + _shownum(total.cpu, 1)
          + head + _shownum(total.tape_store, 1)
          + head + _shownum(total.disk_store, 1)
          + head + _shownum(total.local_store, 1)
          + head + "</th></tr></thead><tbody>";

        sitesfed = Y.Object.values(sitesfed).sort(function(a, b) {
          return d3.ascending(a.country.toLowerCase(), b.country.toLowerCase()); });
       Y.each(sitesfed, function(b){
       var temp_fed_name;
       var temp_id;
       var content_temp="";
       var temp_added = false;
       if(!(b["fed_name"] == "No Federation" )){
       var temp_fed_name = b["fed_name"];
       var fed_cpu = 0; var fed_disk = 0; var fed_tape = 0;
       var fed_country = '';
       var fed_add = false;
       if(temp_fed_name in federationspledges){
         fed_country = federationspledges[temp_fed_name].country;
         if(qyear in federationspledges[temp_fed_name]['pledges'])
          {
            fed_cpu = federationspledges[temp_fed_name]['pledges'][qyear].cpu;
            fed_disk = federationspledges[temp_fed_name]['pledges'][qyear].disk;
            fed_tape = federationspledges[temp_fed_name]['pledges'][qyear].tape;
            fed_add = true;
          }
        }
       temp_fed_name = b["fed_name"].replace(/\s+/g, '-').toLowerCase();
       if(!fed_country){t_country = b["fed_name"].split(" "); fed_country = t_country[0];}
       content_temp += "<tr style='background-color:#dceafe;'>";
       content_temp += "<td class='left'>"+fed_country+"</td>";
       content_temp += "<td class ='left'>";
       content_temp += "<a class='showfedsites' href='#' x-name='"+temp_fed_name+"'>"+b["fed_name"]+"</a>";
       content_temp += "</td><td>"+_shownum(fed_cpu, 0)+"</td>";
       content_temp += "<td>"+_shownum(fed_tape, 0)+"</td><td>"+_shownum(fed_disk, 0)+"</td><td></td><td></td></tr>";
       temp_id = "class='"+temp_fed_name+"' style='display:none;'";
       }
       Y.each(b.sites, function(s) {
         var qkey = (s.canonical_name in pledged
                      ? pledged[s.canonical_name] : null);
          var p = (qkey && qkey[0] in s.resource_pledges
                   ? s.resource_pledges[qkey[0]] : null);
          var espval = null;
          var espval_ins = '';
          var espval = ( s.canonical_name in espcredits
                        ? (qyear in espcredits[s.canonical_name]["esp_values"] ? espcredits[s.canonical_name]["esp_values"][qyear]["esp_credit"] : null) : null)
          if (espval) espval_ins = espval;
          if (fed_add || p || cc || root)
          {
            if(!temp_added){
            content += content_temp; temp_added = true;}
            if(p)
            {
              content +=
              "<tr" + (qkey ? "" : faded) + " "+temp_id+"><td></td><td class='left'>"
              + _self.pledgeLink(instance, s, null, "/" + vquarter)
              + cell + _shownum(p && p.cpu, 1)
              + cell + _shownum(p && p.tape_store, 0)
              + cell + _shownum(p && p.disk_store, 1)
              + cell + _shownum(p && p.local_store, 1)
              + cell;
              if(isgadmin)
              {
                content += "<input class='add-esp-value'"
                + "x-current='"+espval+"'  value='"+espval_ins+"' x-site='"+ s.canonical_name
                +"' x-year='"+ qyear +"' x-element='add-esp-value' type='text' placeholder='New ESP Credit value' style='width:80%'"
                + " /></td></tr>";
              }
              else content += _shownum(p && espval, 2) + "</td></tr>";
            }
            else
            {
            content +=
              "<tr "+temp_id+"><td></td><td class='left'>"
              + _self.pledgeLink(instance, s, null, "/" + vquarter)
              + cell + _shownum(0, 1)
              + cell + _shownum(0, 0)
              + cell + _shownum(0, 0)
              + cell + _shownum(0, 1)
              + cell;
              if(isgadmin)
              {
                content += "<input class='add-esp-value'"
                + "x-current='"+espval+"'  value='"+espval_ins+"' x-site='"+ s.canonical_name
                + "' x-year='"+ qyear +"' x-element='add-esp-value' type='text' placeholder='New ESP Credit value' style='width:80%'"
                + " /></td></tr>";
              }
              else content += _shownum(p && espval, 2) + "</td></tr>";
            }
          }
        });
      });
        content += "</tbody>";
      }
    });
    content += "<thead class='tier'><tr"
      + (summary.npledged ? "" : faded)
      + "><th class='left'>TOTAL"
      + " (" + summary.npledged + ")"
      + head + _shownum(summary.cpu, 1)
      + head + _shownum(summary.tape_store, 1)
      + head + _shownum(summary.disk_store, 1)
      + head + _shownum(summary.local_store, 1)
      + head + " </th>"+head+"</th></tr></thead><tbody>";
    view.content("pledges", content);
    view.render();
    _self.doc.all("button, input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });

    view.on("update-esp-credits", "click", function(e) {
      _updateESPCredits();
    });
  };

  /** Action handler for updating ESP Credits values. */
  var _updateESPCredits = function()
  {
    var update = [];
    var update_message = "";
    var year = "";
    var error_message = "";
    var esp_ele = document.getElementsByClassName('add-esp-value');
    for(var i = 0; i< esp_ele.length; i++)
       {
         var item = esp_ele[i];
         if (item)
         {
           var x_site = X.getDOMAttr(item, "x-site");
           var x_current = X.getDOMAttr(item, "x-current");
           var x_year = X.getDOMAttr(item, "x-year");
           year = x_year;
           var value = item.value;
           if (i==0) update_message = "";
           if (value)
	   {
             if (!(x_current == value))
             {
               update.push({'site': x_site, 'value': value, 'year': x_year});
               update_message += " Site: "+x_site+ " new value: "+ value + " old value: "+ x_current;
               if (!value.match(/^([0-9]{1,10})([.][0-9]{1,})?$/))
               {
                 error_message += "\n Site: "+x_site+", value: "+ value;
                 item.className += " invalid-value";
               }
               else item.className = "add-esp-value";
             }
	   }
         }
       }
    if (update && !error_message)
    {
      X.confirm(Y, "Rewrite ESP credit values for year '" + year + "' with "
                + " these values : " + update_message
                + "?",
                "Update", function() {
                  for (var i=0; i< update.length; i++){
                    _state.modify([{
                      method: "PUT", entity: "esp-credit",
                      data: { "site": update[i].site, "value" : update[i].value, "year" : update[i].year},
                      invalidate: [ "esp-credit" ],
                      message: "Rewriting ESP credit values for '" + year + "'"
                    }]);
                  }
      });
    }
    else if (error_message) {X.confirm(Y,"Problem with these fields: "+ error_message, "Ok", "Cancel")}
  };

  /** Function for converting timestamp to date string */
  var getdate = function(tmp_timestamp)
  {
    var date = new Date(tmp_timestamp * 1000);
    var year = date.getFullYear();
    var month = date.getMonth()+1;
    var day = date.getDate();
    var hour = date.getHours();
    var minute = date.getMinutes();
    if (minute<10) minute = "0" + minute;
    var date_string = year + "-" + month +"-"+ day +" "+ hour + ":" + minute;
    return date_string;
  }

  /** Page for managing site pledges for a given year, with a full
      list of all the site's pledges. For unpriviledged users just show
      the historical pledge information. For global admins and site
      executives allow new pledges to be made. */
  this.quarter = function(req)
  {
    var body, content, quarter, qyear, qpart;
    var now = new Date();
    var curyear = now.getFullYear();
    var quarters = {}, vquarter = unescape(req.params.quarter) || "";
    var site = unescape(req.params.site);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, site, "Pledges");
    _self.loading(state);
    var isadmin = (state.isGlobalAdmin() || state.hasSiteRole("Site Executive", site));
    var qmatch = vquarter && vquarter.match(/^(20(?:0[789]|1[0-9]|20))$/);
    if (! qmatch)
    {
      qyear = curyear;
    }
    else
    {
      qyear = qmatch[1];
    }

    var maxyear = curyear + 3;
    var minyear = Math.min(curyear - 4, 2007);
    var obj = (site in state.sitesByCMS && state.sitesByCMS[site]);
    var pledges = (obj && obj.resource_pledges) || {};
    var site_pledges = (obj && obj.history_resource_pledges) || {};
    Y.each(Object.keys(pledges), function(q) {
      var year = parseInt(q.substring(0, 4));
      minyear = Math.min(minyear, year);
      maxyear = Math.max(maxyear, year);
    });
    for (var year = minyear; year <= maxyear; ++year)
        quarters[year] = year;

    var view = _views.attach("quarter", _self.doc);
    view.value("cpu", "0");   view.validator("cpu", X.rxvalidate(gui.rx.FLOAT));
    view.value("tape", "0");  view.validator("tape", X.rxvalidate(gui.rx.FLOAT));
    view.value("disk", "0");  view.validator("disk", X.rxvalidate(gui.rx.FLOAT));
    view.value("local", "0"); view.validator("local", X.rxvalidate(gui.rx.FLOAT));
    view.on("add", "click", function(e) {
      _addPledge(state, site,
                 view.valueOf("quarter"), view.valueOf("cpu"),
                 view.valueOf("tape"), view.valueOf("disk"), view.valueOf("local"));
    });

    content = "";
    Y.each(Object.keys(quarters).sort(d3.descending), function(q) {
      content +=
        "<option value='" + q + "'"
        + (q == quarter ? " selected='selected'" : "") + ">"
        + quarters[q] + "</option>";
    });
    view.content("quarter", content);
    view.style("edit", "display", isadmin ? "" : "none");

    content = "";
    var cell = "</td><td>";
    Y.each(Object.keys(quarters).sort(d3.descending), function(q) {
      if (q in pledges)
      {
        var temp_class = "class='"+site+"_"+ q +"' style='display:none; background-color:#dceafe'";
        var p = pledges[q];
        content +=
          "<tr><td class='left'>"
          + "<a href=# class='showpledgehistory' x-name='" + site +"_"+q+"'>" + Y.Escape.html(quarters[q]) + "</a>"
          + cell + _shownum(p.cpu, 1)
          + cell + _shownum(p.tape_store, 0)
          + cell + _shownum(p.disk_store, 1)
          + cell + _shownum(p.local_store, 1)
          + "</td></tr>";
       if(q in site_pledges){
        Y.each(site_pledges[q], function(s){
                    content +=
                       "<tr "+ temp_class +"><td class='left'>"
                     + getdate(s.pledge_date)
                     + cell + _shownum(s.cpu, 1)
                     + cell + _shownum(s.tape_store, 1)
                     + cell + _shownum(s.disk_store, 1)
                     + cell + _shownum(s.local_store, 1)
                     + "</td></tr>";

          });
        }
      }
    });
    view.content("table", content);
    view.content("title", Y.Escape.html(site) + " resource pledges");
    content = "";
    if(site in state.federationsByAlias)
    {
    var fedPledges = {};
    var fedName =state.federationsByAlias[site].feder_name;
    if(fedName){
      if(fedName in state.federationsPledges)
        {
        fedPledges = state.federationsPledges[fedName].pledges;
        hist_pledges = state.federationsPledges[fedName].history_pledges;
        Y.each(Object.keys(fedPledges), function(i) {
             var p  = fedPledges[i];
             var temp_fed_name = site+"_"+i+ "_feder";
             var temp_class = "class='"+temp_fed_name+"' style='display:none; background-color:#dceafe'";

             content +=
               "<tr><td class='left'>"
              + "<a href=# class='showpledgehistory' x-name='" + temp_fed_name +"'>" + Y.Escape.html(i) + "</a>"
              + cell + _shownum(p.cpu, 1)
              + cell + _shownum(p.tape, 1)
              + cell + _shownum(p.disk, 1)
              + cell + _shownum(0, 1)
              + "</td></tr>";

        if(i in hist_pledges)
        {
          Y.each(hist_pledges[i], function(s){
             content +=
                       "<tr "+ temp_class +"><td class='left'>"
                     + getdate(s.timestamp)
                     + cell + _shownum(s.cpu, 1)
                     + cell + _shownum(s.tape, 1)
                     + cell + _shownum(s.disk, 1)
                     + cell + _shownum(0, 1)
                     + "</td></tr>";
          });
        }
        });
        }
    }
    }
   view.content("fed-table", content);
   view.render();
  };

  // Handle history controller state.
  gui.history.route("/:instance/pledges", this.main);
  gui.history.route("/:instance/pledges/:site", this.quarter);
  gui.history.route("/:instance/pledges/:site/:quarter", this.quarter);

  return this;
});
