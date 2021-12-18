
def print_request(req):
	[url, query, *_] = [*req.get_full_url().split('?'), '']
	query = query.split('&')
	method = req.get_method()
	headers = req.headers
	data = req.data

	line_len = max([len(method + " " + url), len(str(headers)), len(str(data))])
	def print_to_len(text):
		text = str(text)
		padding = ' ' * (line_len - len(text))
		print('# ' + text + padding + " #")

	def print_chars_to_len(char):
		print('# ' + (char * line_len) + " #")


	print_chars_to_len('#')
	print_to_len(method + " " + url)
	print_chars_to_len('=')

	print_to_len('QUERY:')
	print_to_len('---------')
	[print_to_len(q) for q in query]
	print_chars_to_len(' ')

	print_to_len('HEADERS:')
	print_to_len('---------')
	print_to_len(headers)
	print_chars_to_len(' ')

	print_to_len('BODY:')
	print_to_len('---------')
	print_to_len(data)
	print_chars_to_len('#')
	
	



# import urllib.parse
# import urllib.request

# req = urllib.request.Request('http://localhost:3000')
# with urllib.request.urlopen(req) as response:
#    the_page = response.read()
#    print(the_page)


# # url = 'http://www.someserver.com/cgi-bin/register.cgi'
# url = 'http://localhost:3000'
# values = {'name' : 'Michael Foord',
#           'location' : 'Northam&"pton',
#           'language' : 'Python' }

# import json

# data = urllib.parse.urlencode(values)
# # data = data.encode('ascii') # data should be bytes
# # req = urllib.request.Request(url+"?"+data, data=json.dumps(values).encode('utf-8'), headers={'Content-Type': 'text/json'})
# # req = urllib.request.Request(url, data=json.dumps(values).encode('utf-8'), headers={'Content-Type': 'text/json'})
# req = urllib.request.Request(url+"?"+data, method='POST', headers={'Content-Type': 'text/json'})
# # req = urllib.request.Request(url, method='POST', data=json.dumps(values).encode('utf-8'), headers={'Content-Type': 'text/json'})
# print(data)

# # print(req.get_full_url())
# # print(req.get_method())
# # print(req.headers)
# # print(req.data)
# # print(dir(req))  # list lots of other stuff in Request

# print_request(req)

# with urllib.request.urlopen(req) as response:
#    the_page = response.read()
#    print(the_page)

# while True:
# 	with urllib.request.urlopen(req) as response:
# 		the_page = response.read()
# 		print(the_page)
# 	pass





import urllib.parse
import urllib.request

req = urllib.request.Request('http://localhost:3000')
with urllib.request.urlopen(req) as response:
   the_page = response.read()
   print(the_page)


# url = 'http://www.someserver.com/cgi-bin/register.cgi'
url = 'http://localhost:3000'
values = {'name' : 'Michael Foord',
          'location' : 'Northam&"pton',
          'language' : 'Python' }

import json

data = urllib.parse.urlencode(values)
req = urllib.request.Request(url+"?"+data, method='POST', headers={'Content-Type': 'text/json'})

print_request(req)

with urllib.request.urlopen(req) as response:
   the_page = response.read()
   print(the_page)


listen_req = urllib.request.Request(url+"?"+data, method='POST', headers={'Content-Type': 'text/json'})
while True:
	with urllib.request.urlopen(listen_req) as response:
		the_page = response.read()
		print(the_page)
	