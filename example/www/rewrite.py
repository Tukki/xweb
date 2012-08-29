
rewrite_rules = [
        ('/help.html', {'c':'default', 'a':'help'},),
        ('/<a|short|long>/<short_id|\d+>.htm', {'c':'default'}),
        ('/<a|(short|long)>/11.htm', {'c':'default'}),
]


#rewrite_rules = Map([
#    Rule('/', endpoint='new_url'),
#    Rule('/<short_id>', endpoint='follow_short_link'),
#    Rule('/<short_id>+', endpoint='short_link_details')
#])
