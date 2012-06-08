

rewrite_rules = [
        ('/help.html', 'c=default&a=help',),
        ('/<short_id>.htm', 'c=default&a=short',),
]


#rewrite_rules = Map([
#    Rule('/', endpoint='new_url'),
#    Rule('/<short_id>', endpoint='follow_short_link'),
#    Rule('/<short_id>+', endpoint='short_link_details')
#])
