# Yelp Road Trip
![logo](https://raw.github.com/aok1425/yelp-road-trip-app/master/static/logo.png "")

This is a way to search Yelp by time. Let's say you're going on a road trip, but you don't know where you'll be around dinner time. That's what this app is for!

##How it works:
The app calcuates your location at the time you want to eat, and does Yelp searches there, 15 minutes before there, and up to 45 minutes after there. It then shows the 9 restaurants with the most number of reviews.

The 'find the best' option is like the regular option, but it searches along the entire route, except for nearby the start and endpoints. The longer the route is, the more points it will search, and the longer the search will take.

##Wish List:
* State the destination arrival time on the front page after the first three boxes are inputted.
* Allow more than one concurrent user. :)
* Make panel like the on the Yelp app to see all your results at once.
* Add price information (e.g. $$$) using Foursquare's API.
* Show only restaurants that will be open at arrival time, using Locu API.
* Input validation/typeahead on locations, using WTForms under Flask.

Send me feedback! I'm at @aok1425 or the same Twitter handle on GMail. Or, via [GitHub Issues](https://github.com/aok1425/yelp-road-trip-app/issues). Thanks to [Adam Wagner](https://github.com/AdamWagner) for designing and implementing the front page, and [Feifan Wang](https://github.com/4thethrillofit) for telling me how to put this app on the internet.

##Known issues:
* Might not work if eating time is intended to be the next day. Same-day only!
* Estimated times and distances to restaurant don't incorporate live traffic data. Google doesn't allow this when you ask it multiple directions at the same time.
* Some estimated times and distances are crazy. If Google can't understand Yelp's address, I just changed that address to my old house.



##Other quandaries:

####Finding the appropriate places to search:
For really long steps, like going on the highway for 100 miles, if that step is greater than too_long_step, the program divides that step's duration by time_block. It adds the endpoint of that step, for cases where the step doesn't divide evenly into time_block.

Now, there is a "table" of steps, with the long steps divided by time_block. The program then makes a new "table", using only each step after cull_block*n. So if cull_block is set to 30, the program will take each step after 30 mins, 60 mins, etc. to make the new "table".

A possible improvement on this would be to divide the big steps according to their position amongst all the steps before it, not according to itself. When big steps are divided, the program uses Bing Maps API to get a list of coordinate points after some interval. The program then divides this list of points by cull_block. So, setting cull_block to be small and dividing up even "small" steps would use the Bing Maps API more.

####Improving the results:
Yelp can either search by their own "best" algorithm, by distance, or by highest rated. Ways #1 and 3 both privilege closeness to the search point. Originally, I'd wanted to find all the restaurants along a route, then take only the most reviewed out of those. If Yelp updates their API to find the most reviewed--which you can do on their website--then I just need search points roughly every 40,000 meters. (Yelp's max search distance is 40,000 meters, and this assumes a straight line route.)

####Speeding it up:
I think the main slowdown comes from doing Yelp searches at each point. I don't know how to have multiple searches running at the same time, and I don't think Yelp allows for multiple search points being passed to it at one time.

It's probably possible to vectorize some of the other for loops, and/or implement more efficient data structures. Like, if I didn't use Pandas...

####Restaurants with the same name:
Because both `resto_table` and `filtered_table` are dictionaries, if two restaurants have the same name, one replaces the other. Should probably implement a different data structure (Pandas DataFrame?) to fix this.

####Displaying more than 9 results:
I set 9 because that's the limit for Google Directions Matrix. If someone can find a way to break up all the restaurants-to-be-displayed into chunks of 9 or smaller, pass Google Directions Matrix API each of these chunks, then compile the end result, that would be great. 

##How the program works:
* Program plugs start and end locations into Google Maps. It gets directions back.
* Take steps longer than too_long_step and break their duration by time_block.
* Cull_search_points() filters out only the points that occur every cull_block minutes.
* Then, the program either filters these search points by eating_time_start, or, if the 'just find the best' button was clicked, it takes away the 2 starting and 3 ending search points.
* The program does Yelp searches in each of these points, which returns search_limit number of restaurants (the max being 20), and after sorting this list by number of reviews, it puts the return_limit number of restaurants into the dictionary resto_table.
* The review_cutoff-most reviewed restaurants go into filtered_table.
* The program gets from Google Distance Matrix API the time and distance to each of the restaurants in filtered_table, and the extra time and distance to drive there.
* It puts this information into filtered_table.
* It makes an Google map HTML file from filtered_table and puts it in \static\map.html.