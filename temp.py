# addresses from filtered table made into a list: [filtered_table[name][0] for name in filtered_table.keys()]
# assuming, once again, that when I call filtered_table.keys(), it will always be the same...

def extra_distance_json(start, end, list_of_restos, sensor='false'):
	"""Returns JSON response for extra distance to resto address.
	GMaps Directions Matrix API accepts a max of 9 restos, making 11 elements including start and end."""
	key='AIzaSyBsbGsLbD2hM5jr1bewKc6hotr3iV1lpmw'
	
	origins=[start]
	destinations=[end]
	[origins.append(resto) for resto in list_of_restos]
	[destinations.append(resto) for resto in list_of_restos]	
	
	payload = {'origins':'|'.join(origins), 'destinations':'|'.join(destinations), 'key':key, 'units':'imperial', 'sensor':sensor}
	url = 'https://maps.googleapis.com/maps/api/distancematrix/json'

	r = requests.get(url, params=payload)
	#print 'URL: %s' % (r.url,)
	print len(list_of_restos),'restos, ',len(list_of_restos)+2,' elements.'
	#return r.url
	return r.json()

def extra_distance_to_resto(thejson):
	"""Takes in a JSON from Google Distance Matrix API and returns the diff to go to resto, in time and distance."""
	durations,distances=[],[]
	num_elements=len(thejson['rows'])
	
	for row in thejson['rows']:
		for element in row['elements']:
			try:
				distances.append(element['distance']['value']) # in seconds
				durations.append(element['duration']['value']) # in meters
			except KeyError:
				print 'GMaps can\'t understand an address. Program will crash here...'
				print 'what is',row
				print 'what is',element
	
	first_element_duration=durations[1:num_elements]
	second_element_duration=[durations[len(durations)-n*num_elements] for n in range(1,num_elements)]
	diff_list_duration=[durations[0]-first_element_duration[i]-second_element_duration[i] for i in range(len(first_element_duration))]
	
	first_element_distance=distances[1:num_elements]
	second_element_distance=[distances[len(distances)-n*num_elements] for n in range(1,num_elements)]
	diff_list_distance=[distances[0]-first_element_distance[i]-second_element_distance[i] for i in range(len(first_element_distance))]
	
	original_route_list_duration=durations[1:num_elements]
	original_route_list_distance=distances[1:num_elements]

	return diff_list_duration,diff_list_distance,original_route_list_duration,original_route_list_distance