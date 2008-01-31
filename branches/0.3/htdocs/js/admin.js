$.fn.extend({
    initDl: function() {
        return this.each(function() {
            var obj = this;

            $(this).children('dd').initDd();
            $(this).children('dt').initDt();
            $(this).find('a.editable').editable();

            $(
                '<a class="toggle" href="#" title="Hide">' + 
                '<img src="images/icons/bullet_arrow_up.png" />' +
                '</a>'
            ).prependTo(this).find(
                'img'
            ).click(function() {
                if ($(this).attr('src') == 'images/icons/bullet_arrow_up.png') {
                    $(obj).children('dt,dd').hide();
                    $(this).attr('src', 'images/icons/bullet_arrow_down.png');
                    $(this).parent('a').attr('title', 'Show');
                } else {
                    $(obj).children('dt').show();
                    $(obj).children('dd').not('.hidden').show();
                    $(this).attr('src', 'images/icons/bullet_arrow_up.png');
                    $(this).parent('a').attr('title', 'Hide');
                }
            });

            $(
                '<a href="#" title="Remove this object">' + 
                '<img src="images/icons/application_form_delete.png" />' + 
                '</a>'
            ).prependTo(this).find(
                'img'
            ).click(function() {
                $(obj).remove();
            });

            $(
                '<a href="#" title="Add new attribute">' + 
                '<img src="images/icons/key_add.png" />' + 
                '</a>'
            ).prependTo(this).find(
                'img'
            ).click(function() {
                $(obj).children('dt').show();
                $(obj).children('dd').not('.hidden').show();
                $(obj).children('a.toggle').attr(
                    'title', 'Hide'
                ).find('img').attr(
                    'src', 'images/icons/bullet_arrow_up.png'
                );
                $(
                    '<dt><a href="#" class="editable action">attribute</a></dt>'
                ).appendTo(obj).initDt().find(
                    'a.editable'
                ).editable().click();
            });
        });
    },

    initDd: function() {
        return this.each(function() {
            var obj = this;

            if ($(this).children().get(0).tagName == 'DL') {
                $(this).children('dl').initDl();
            } else {
                $(
                    '<a href="#" title="Remove this value">' + 
                    '<img src="images/icons/textfield_delete.png" />' +
                    '</a>'
                ).appendTo(this).click(function() {
                    $(obj).remove();
                });
            }
        });
    },

    initDt: function() {
        return this.each(function() {
            var obj = this;

            $(
                '<a href="#" title="Add new value">' + 
                '<img src="images/icons/textfield_add.png" />' + 
                '</a>'
            ).appendTo(this).find(
                'img'
            ).click(function() {
                last = obj;
                $(obj).nextAll().each(function() {
                    if (this.tagName != 'DD') return false;
                    $(this).show();
                    $(this).removeClass('hidden');
                    last = this;
                });
                $(obj).children('a.toggle').attr(
                    'title', 'Hide'
                ).find('img').attr(
                    'src', 'images/icons/bullet_arrow_up.png'
                );
                $(
                    '<dd><a href="#" class="editable action">value</a></dd>'
                ).insertAfter(last).initDd().find(
                    'a.editable'
                ).editable().click();
            });

            $(
                '<a href="#" title="Add new object">' + 
                '<img src="images/icons/application_form_add.png" />' + 
                '</a>'
            ).appendTo(this).find(
                'img'
            ).click(function() {
                last = obj;
                $(obj).nextAll().each(function() {
                    if (this.tagName != 'DD') return false;
                    $(this).show();
                    $(this).removeClass('hidden');
                    last = this;
                });
                $(obj).children('a.toggle').attr(
                    'title', 'Hide'
                ).find('img').attr(
                    'src', 'images/icons/bullet_arrow_up.png'
                );
                $(
                    '<dd><dl></dl></dd>'
                ).insertAfter(last).find(
                    'dl'
                ).initDl();
            });

            $(
                '<a href="#" title="Remove this attribute">' + 
                '<img src="images/icons/key_delete.png" />' + 
                '</a>'
            ).appendTo(this).find(
                'img'
            ).click(function() {
                $(obj).nextAll().each(function() {
                    if (this.tagName != 'DD') return false;
                    $(this).remove();
                });
                $(obj).remove();
            });

            $(
                '<a class="toggle" href="#" title="Hide">' + 
                '<img src="images/icons/bullet_arrow_up.png" />' +
                '</a>'
            ).appendTo(this).find(
                'img'
            ).click(function() {
                if ($(this).attr('src') == 'images/icons/bullet_arrow_up.png') {
                    $(obj).nextAll().each(function() {
                        if (this.tagName != 'DD') return false;
                        $(this).addClass('hidden');
                        $(this).hide();
                    });
                    $(this).attr('src', 'images/icons/bullet_arrow_down.png');
                    $(this).parent('a').attr('title', 'Show');
                } else {
                    $(obj).nextAll().each(function() {
                        if (this.tagName != 'DD') return false;
                        $(this).removeClass('hidden');
                        $(this).show();
                    });
                    $(this).attr('src', 'images/icons/bullet_arrow_up.png');
                    $(this).parent('a').attr('title', 'Hide');
                }
            });
        });
    },

    editable: function() {
        return this.each(function() {
            $(this).click(function() {
                var obj = this;
                $(obj).hide();
                $(
                    '<input type="text" />'
                ).attr(
                    'value', $(obj).text()
                ).insertAfter(
                    obj
                ).keypress(function(e) {
                    // 13 is Enter, 0 is Esc.
                    if (e.which == 13) {
                        $(obj).text(this.value || 'value');
                        $(obj).show();
                        $(this).remove();
                    } else if (e.which == 0) {
                        $(obj).show();
                        $(this).remove();
                    }
                }).blur(function() {
                    $(obj).text(this.value || 'value');
                    $(obj).show();
                    $(this).remove();
                }).each(function() {
                    this.focus();
                    this.select();
                });
            });
        });
    },

    entryEdit: function() {
        return this.each(function() {
             $('#edit').html('');
             $(this).initDl().appendTo('#edit');

             $(
                 '<a href="#" title="Delete document">' + 
                 '<img src="images/icons/database_delete.png" />' + 
                 '</a>'
             ).prependTo('#edit dl').click(function() {
                 $(this).entryRemove();
             });

             $(
                 '<a href="#" title="Save document">' + 
                 '<img src="images/icons/database_save.png" />' + 
                 '</a>'
             ).prependTo('#edit dl').click(function() {
                 $(this).entrySave();
             });
        });
    },

    entryRemove: function() {
        return this.each(function() {
            img = $(this).find('img').get(0);
            $(img).attr('src', 'images/icons/time.png');
            entry = domToJson($('#edit dl').get(0));
            id = entry.__id__;
            if (confirm('Are you sure you want to delete the document "' + id + '"?')) {
                em.remove(id, {
                    success: function(entry) {
                        $(img).attr('src', 'images/icons/accept.png');
                        $('#edit dl').fadeOut('slow', function() {
                            $('#edit dl').remove();
                        });
                        $('ul#entries').find(
                            'a:contains(' + id+ ')'
                        ).parent().slideUp('slow', function() {
                            $(this).remove();
                        });
                    },
                    error: function(entry) {
                        $(img).attr('src', 'images/icons/error.png');
                    }
                });
            }
        });
    },

    entrySave: function() {
        return this.each(function() {
            img = $(this).find('img').get(0);
            $(img).attr('src', 'images/icons/time.png');
            entry = domToJson($('#edit dl').get(0));
            id = entry.__id__;
            method = id ? 'update' : 'create'; 
            em[method](entry, {
                success: function(entry) {
                    $(img).attr('src', 'images/icons/accept.png');
                    $('#edit dl').fadeOut('slow', function() {
                        $('#edit dl').remove();
                    });
                    if (!id) {
                        $(
                            '<li><a href="#" class="action" title="Edit this document">' + 
                            entry.__id__ + 
                            '</a></li>'
                        ).hide().insertAfter(
                            $('#new').parent()
                        ).fadeIn('slow').find('a').click(function() {
                            jsonToDom(entry).entryEdit();
                        });
                    }
                },
                error: function(entry) {
                    $(img).attr('src', 'images/icons/error.png');
                }
            });
        });
    }
});

function jsonToDom(entry) {
    var dom = $('<dl></dl>');
    for (attr in entry) {
        if ((attr != '__id__') && (attr != '__updated__')) {
            dom.append('<dt><a href="#" class="editable action">' + attr + '</a></dt>');
        } else {
            dom.append('<dt>' + attr + '</dt>');
        }

        values = entry[attr];
        if (!(values instanceof Array)) values = [values];
        $.each(values, function(i, value) {
            if (value instanceof Object) {
                $('<dd></dd>').appendTo(dom).append(jsonToDom(value));
            } else {
                $('<dd><a href="#" class="editable action">' + value + '</a></dd>').appendTo(dom);
            }
        });
    }
    return dom;
}

function domToJson(dl) {
    var entry = {};
    $(dl).children('dt').each(function() {
        var k = $(this).text();
        var v = [];
        $(this).nextAll().each(function() {
            if (this.tagName != 'DD') return false;
            var child = $(this).children().get(0);
            if (child.tagName == 'DL') {
                v.push(domToJson(child));
            } else {
                v.push(parseValue($(this).text()));
            }
        });
        if (v.length == 1) v = v[0];
        entry[k] = v;
    });
    if ((entry.__id__ == 'leave blank for auto-generated') || (entry.__id__ == '')) delete entry.__id__;
    if ((entry.__updated__ == 'leave blank for current time') || (entry.__updated__ == '')) delete entry.__updated__;
    return entry;
}

function parseValue(value) {
    if (/^([+-])?\d+(\.\d+)?(e([+-])?\d+)?$/.exec(value)) {
        return parseFloat(value);
    } else {
        return value;
    }
}
