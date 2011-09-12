SiteDB.Views.Sites = new function()
{
  var _canvas = $('canvas');
  this.attach = function(gui) {}
  this.detach = function()
  {
    while (_canvas.firstChild)
      _canvas.removeChild(_canvas.firstChild);
  }

  this.update = function(data)
  {
    var content = "";
    if (_canvas.innerHTML != content)
      _canvas.innerHTML = content;
  }

  return this;
}();
