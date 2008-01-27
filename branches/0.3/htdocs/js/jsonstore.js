var xml = window.ActiveXObject ? new ActiveXObject("Microsoft.XMLHTTP") : new XMLHttpRequest();

function json(method, url, obj, callback) {
    xml.open(method || 'GET', url, true);
    xml.setRequestHeader('Content-Type', 'application/json');
    xml.onreadystatechange = function() {
        if (xml.readyState == 4) {
            if (callback) {
                callback(xml.responseText);
            }
        }
    };
    xml.send(JSON.stringify(obj));
}
    
function EntryManager(url, common) {
    this.url = url;
    this.common = common;

    this.create = function(entry, callback) {
        for (key in this.common) entry[key] = this.common[key]; 
        json('POST', this.url, entry, callback);
    };

    this.update = function(entry, callback) {
        json('PUT', this.url + entry['__id__'], entry, callback);
    };

    this.search = function(key, callback) {
        json('GET', this.url + encodeURIComponent(JSON.stringify(key)), null, callback);
    };

    // ``delete`` is a reserved word.
    this.remove = function(id, callback) {
        json('DELETE', this.url + id, null, callback);
    };

    this.count = function(key, callback) {
        xml.open('HEAD', this.url + encodeURIComponent(JSON.stringify(key)), true);
        xml.setRequestHeader('Content-Type', 'application/json');
        xml.onreadystatechange = function() {
            if (xml.readyState == 4) {
                if (callback) {
                    callback(parseInt(xml.getResponseHeader("x-items")));
                }
            }
        };
        xml.send('');
    };    
}
