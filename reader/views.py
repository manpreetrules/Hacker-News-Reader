from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.template import RequestContext
import reader.cache as cache
from reader.models import Stories, HNComments, Poll, UserInfo
from django.core import management
import reader.utils as utils
from django.core.urlresolvers import reverse


# This is not a real view, but is used from other views
def custom_message_view(request, message, context_instance):
	response = render_to_response("templates/message.html", {'message': message}, context_instance)
	return response


def index(request, story_type='news', json=False):
	c = {}
	if json:
		template = 'templates/index_json.html'
	else:
		template = 'templates/index.html'
	try:
		page = int(request.GET.get('page'))
	except (ValueError, TypeError):
		page = 1

	try:
		over = int(request.GET.get('over'))
	except (ValueError, TypeError):
		over = None

	limit = request.GET.get('limit', None)
	if not limit:
		limit = request.COOKIES.get('stories_limit')
	try:
		limit = int(limit)
	except (ValueError, TypeError):
		limit = 25

	context_instance = RequestContext(request)
	try:
		cache.update_stories(story_type=story_type, over_filter=over)
		stories = cache.stories(page, limit, story_type=story_type, over_filter=over)
	except utils.ShowAlert, e:
		c['alerts'] = [{'message': e.value, 'level': 'error'}]
		return render_to_response(template, c, context_instance)
	pages = stories.paginator.page_range
	visible_pages = 6
	if stories.paginator.num_pages > visible_pages:
		diff = visible_pages / 2
		if page > diff:
			left = page - diff
			right = page + diff
			if stories.paginator.num_pages - page < diff:
				left -= diff - (stories.paginator.num_pages - page)
		else:
			left = 0
			right = visible_pages
		pages = pages[left:right]
	c.update({"stories": stories, "pages": pages, 'limit': limit})
	response = render_to_response(template, c, context_instance)
	response.set_cookie('stories_limit', limit)
	return response


def comments(request, commentid, json=False):
	if commentid:
		try:
			commentid = int(commentid, 10)
		except ValueError:
			commentid = None
	if json:
			template = 'templates/comments_json.html'
	else:
		template = 'templates/comments.html'
	context_instance = RequestContext(request)
	# Context
	c = {'story': None, 'polls': None, 'total_votes': 0}
	try:
		cache.update_comments(commentid=commentid)
		c['nodes'] = cache.comments(commentid)
	except utils.ShowAlert, e:
		c['alerts'] = [{'message': e.value, 'level': 'error'}]
	try:
		c['story'] = Stories.objects.get(pk=commentid)
		if c['story'].poll:
			c['polls'] = Poll.objects.filter(story_id=commentid).order_by('id')
			for poll in c['polls']:
				c['total_votes'] += poll.score
	except Stories.DoesNotExist:
		try:
			c['nodes'] = HNComments.objects.get(id=commentid, dead=False).get_descendants(True)
			node_first = c['nodes'][0]
			if node_first:
				try:
					c['story'] = Stories.objects.get(pk=node_first.story_id)
				except Stories.DoesNotExist:
					c['story'] = None
			c['perma'] = True
		except HNComments.DoesNotExist:
			c['alerts'] = [{'message': e.value, 'level': 'error'}]
	return render_to_response(template, c, context_instance)


def userpage(request, username, json=False):
	c = {}
	if json:
		template = 'templates/user_json.html'
	else:
		template = 'templates/user.html'
	context_instance = RequestContext(request)
	try:
		cache.update_userpage(username=username)
		c['userinfo'] = cache.userinfo(username)
	except UserInfo.DoesNotExist:
		c['alerts'] = [{'message': 'User not found'}]
	except utils.ShowAlert, e:
		c['alerts'] = [{'message': e.value, 'level': 'error'}]
	return render_to_response(template, c, context_instance)


def command(request, command):
	# Secure this with some admin login
	# Although there isn't really anything bad you can do with it
	if command == 'migrate':
		management.call_command('migrate', all_apps=True)
		response = 'Command executed'
	elif command == 'collectstatic':
		management.call_command('collectstatic', interactive=False)
		response = 'Command executed'
	else:
		response = 'Command not found'
	return HttpResponse(response)
