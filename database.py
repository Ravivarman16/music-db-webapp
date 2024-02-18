from google.cloud import secretmanager_v1beta1
from modules import pg8000

def get_secret(secret_id):
    client = secretmanager_v1beta1.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    payload = response.payload.data.decode("UTF-8")
    return payload

def database_connect():
    try:
        # Fetch database details from Google Secret Manager
        database = get_secret("database_secret")
        user = get_secret("user_secret")
        password = get_secret("password_secret")
        host = get_secret("host_secret")

        # Use the database details retrieved from Secret Manager to connect to the database
        connection = pg8000.connect(database=database, user=user, password=password, host=host)
        return connection
    except Exception as e:
        print("Error connecting to the database:", str(e))
        return None

# Replace project_id with your actual Google Cloud project ID
project_id = get_secret("project_id")


##################################################
# Print a SQL string to see how it would insert  #
##################################################

def print_sql_string(inputstring, params=None):
    """
    Prints out a string as a SQL string parameterized assuming all strings
    """

    if params is not None:
        if params != []:
           inputstring = inputstring.replace("%s","'%s'")
    
    print(inputstring % params)

#####################################################
#   SQL Dictionary Fetch
#   useful for pulling particular items as a dict
#   (No need to touch
#       (unless the exception is potatoing))
#   Expected return:
#       singlerow:  [{col1name:col1value,col2name:col2value, etc.}]
#       multiplerow: [{col1name:col1value,col2name:col2value, etc.}, 
#           {col1name:col1value,col2name:col2value, etc.}, 
#           etc.]
#####################################################

def dictfetchall(cursor,sqltext,params=None):
    """ Returns query results as list of dictionaries."""
    
    result = []
    if (params is None):
        print(sqltext)
    else:
        print("we HAVE PARAMS!")
        print_sql_string(sqltext,params)
    
    cursor.execute(sqltext,params)
    cols = [a[0].decode("utf-8") for a in cursor.description]
    print(cols)
    returnres = cursor.fetchall()
    for row in returnres:
        result.append({a:b for a,b in zip(cols, row)})
    # cursor.close()
    return result

def dictfetchone(cursor,sqltext,params=None):
    """ Returns query results as list of dictionaries."""
    # cursor = conn.cursor()
    result = []
    cursor.execute(sqltext,params)
    cols = [a[0].decode("utf-8") for a in cursor.description]
    returnres = cursor.fetchone()
    result.append({a:b for a,b in zip(cols, returnres)})
    return result

#####################################################
#####################################################
#####################################################
###########  Additional Task - MEDIUM     ###########
#####################################################
#####################################################

#####################################################
#   Film Genre  - Multi Term Search
#   
#####################################################
def search_filmgenre_multi(inDict):
    """
    Searches for matching film genre contents by given filters
    Input Examples-> 
    1. mediaType:movie,name:The Shawshank Redemption,genre:drama,year:>1993
    2. mediaType:all,genre:drama,year:>2009
    3. mediaType:tvshow,name:Friends
    4. mediaType:movie,genre:drama,year :>1993
    5. mediaType:tvshow, genre: drama
    6. mediaType:movie ,genre :drama,year:BETWEEN 1993 AND 2009
    7. mediaType:tvshowep
    8. mediaType:tvshowep,epname:The One Where Monica Gets A Roommate
    9. mediaType:tvshowep,showname:The Friends
    10. mediaType:tvshowep,showname:Friends,episode:10
    10. mediaType:tvshowep,showname:Friends,season:1,episode:10
    11. mediaType:tvshowep,showname:Friends,season:2
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:


        sql_template_movie = """SELECT M.movie_id as item_id, M.movie_title as item_title, 'Movie' as item_type
                            FROM mediaserver.movie M LEFT OUTER JOIN mediaserver.mediaitemmetadata mimd on (m.movie_id = mimd.media_id)
                            JOIN mediaserver.Metadata md on (mimd.md_id = md.md_id)
                            JOIN mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)"""

        sql_template_tvshow = """ SELECT T.tvshow_id as item_id, T.tvshow_title as item_title, 'TV Show' as item_type
                FROM mediaserver.tvshow T left outer join mediaserver.TVEpisode TE on (T.tvshow_id = TE.tvshow_id)
                    JOIN mediaserver.TVShowMetaData  TVMD on (TE.tvshow_id = TVMD.tvshow_id)
                    JOIN mediaserver.Metadata md on (TVMD.md_id = md.md_id)
                    JOIN mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)"""

        sql_template_tvshowep = """SELECT te.media_id as item_id, te.tvshow_episode_title as item_title, 'TV Show Episode' as item_type
                                FROM mediaserver.tvshow T left outer join mediaserver.TVEpisode te on (T.tvshow_id = te.tvshow_id)
                                left outer join
                                (mediaserver.mediaitemmetadata natural join mediaserver.metadata natural join mediaserver.MetaDataType) md
                                on (te.media_id=md.media_id)"""

        sql_ending = """ group by item_id, item_title, item_type
                            order by  item_id"""

        
        where_clause = " WHERE md.md_type_id = 2 "
        
        if inDict["mediaType"] == "movie":

            if "name" in inDict:
                where_clause =  where_clause + "AND "+ "M.movie_title = '{}' ".format(inDict["name"])
            if  "genre" in inDict:
                where_clause =  where_clause + "AND " +  "md.md_value = '{}' ".format(inDict["genre"])
            if "year" in inDict:
               where_clause =  where_clause + "AND " +  "M.release_year {} ".format(inDict["year"])
            final_sql = sql_template_movie + where_clause + sql_ending

        elif inDict["mediaType"] == "tvshow":
            if "name" in inDict:
                where_clause =  where_clause + "AND "+ "T.tvshow_title = '{}' ".format(inDict["name"])
        
            if  "genre" in inDict:
                where_clause =  where_clause + "AND " +  "md.md_value = '{}' ".format(inDict["genre"])
            final_sql = sql_template_tvshow + where_clause + sql_ending

        elif inDict["mediaType"] == "tvshowep":
            where_clause = " WHERE md.md_type_id IN (2,3,4,5,6) "
            if "epname" in inDict:
                where_clause = where_clause + "AND " + "te.tvshow_episode_title = '{}' ".format(inDict["epname"])
            if "season" in inDict and "showname" in inDict:
                where_clause = where_clause + "AND " + "te.season = {} AND T.tvshow_title = '{}' ".format(inDict["season"],inDict["showname"])
            if "episode" in inDict and "showname" in inDict:
                where_clause = where_clause + "AND " + "te.episode = {} AND T.tvshow_title = '{}' ".format(inDict["episode"],inDict["showname"])
            
            # if "date" in inDict:
            #     print("hi")
            #     if inputDict["date"][0] == '>' or inputDict['date'][0] == '<': #e.g., date:>2017-01-01
            #         where_clause = where_clause + " AND te.air_date {} '{}'".format(inputDict["date"][0], inputDict["date"][1:])
            #     elif inputDict["date"][0:2] == '>=' or inputDict['date'][0:2] == '<=': #e.g., publish_date:>=2017-01-01
            #         where_clause = where_clause + " AND te.air_date {} '{}'".format(inputDict["date"][0:2], inputDict["date"][2:])
            #     elif inputDict["date"].split()[0].lower() == 'between': 
            #         where_clause = where_clause + " AND te.air_date BETWEEN '{}' AND '{}'".format(inputDict["date"].split()[1], inputDict["date"].split()[3])
            #     else: #e.g., publish_date:2018-01-11
            #         where_clause = where_clause + " AND te.air_date = '{}'".format(inputDict["date"])
                
            final_sql = sql_template_tvshowep + where_clause + sql_ending
            


        elif inDict["mediaType"] == "all":
            where_clausem = ""
            if  "genre" in inDict:
                where_clause = where_clause + "AND " +  "md.md_value = '{}' ".format(inDict["genre"])
                

            if "year" in inDict:
               where_clausem =  where_clause + "AND " +  "M.release_year {} ".format(inDict["year"])
           
            
            final_sql = "(" + sql_template_movie + where_clausem +  sql_ending+")"+ " UNION " + "(" + sql_template_tvshow + where_clause + sql_ending+")"


        r = dictfetchall(cur,final_sql)
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Error Couldn't Search for the Movie in Advanced Search")

    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Podcast Genre  - Multi Term Search
#   
#####################################################
def search_podcastep_podcast_multi(inputDict):
    """
    Podcast – name of podcast and/or release date  - Theresa
	Podcast Ep – name of episode and/or release date
    - name, publish_date, length


    sample input:
    mediaType: podcast, date : >2019-01-01
    mediaType: all, date : 2019-01-01
    mediaType: all, date : between 2018-01-01 and 2019-01-12, length: 4462
    mediaType: podcastep, name: Fine Cotton Fiasco bonus episode
    mediaType: all, date : between 2018-01-01 and 2019-01-01, length: > 300
    """



    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()

    sql_template_podcastep = """
    SELECT distinct podep.media_id as item_id, podcast_episode_title as item_title, 'PodcastEp' as item_type
    FROM mediaserver.podcastepisode podep LEFT OUTER JOIN 
        (mediaserver.mediaitemmetadata NATURAL JOIN mediaserver.metadata NATURAL JOIN mediaserver.metadatatype) mediamd 
        ON (podep.media_id = mediamd.media_id)
    """

    sql_template_podcast = """
    SELECT distinct pod.podcast_id as item_id, podcast_title as item_title, 'Podcast' as item_type
        FROM mediaserver.podcast pod LEFT OUTER JOIN 
            (mediaserver.podcastmetadata NATURAL JOIN mediaserver.metadata NATURAL JOIN mediaserver.metadatatype) p_to_md 
            ON (pod.podcast_id = p_to_md.podcast_id)
    """


    where_clause = " WHERE true" #podcast genre

    endclause = " ORDER BY item_id"

    if inputDict["mediaType"] == "podcastep":
        if "name" in inputDict:
            name = inputDict["name"].lower()
            apostrophe_index = name.find("'")
            if apostrophe_index >= 0:
                name = name[:apostrophe_index] + "'" + name[apostrophe_index:]
            where_clause = where_clause + " AND lower(podcast_episode_title) = '{}'".format(name)
        if "date" in inputDict:
            if inputDict["date"][0] == '>' or inputDict['date'][0] == '<': #e.g., publish_date:>2017-01-01
                where_clause = where_clause + " AND podcast_episode_published_date {} '{}'".format(inputDict["date"][0], inputDict["date"][1:])
            elif inputDict["date"][0:2] == '>=' or inputDict['date'][0:2] == '<=': #e.g., publish_date:>=2017-01-01
                where_clause = where_clause + " AND podcast_episode_published_date {} '{}'".format(inputDict["date"][0:2], inputDict["date"][2:])
            elif inputDict["date"].split()[0].lower() == 'between': 
                where_clause = where_clause + " AND podcast_episode_published_date BETWEEN '{}' AND '{}'".format(inputDict["date"].split()[1], inputDict["date"].split()[3])
            else: #e.g., publish_date:2018-01-11
                where_clause = where_clause + " AND podcast_episode_published_date = '{}'".format(inputDict["date"])
        if "length" in inputDict:
            if inputDict["length"][0] == '>' or inputDict["length"][0] == '<' or inputDict["length"].split()[0].lower() == 'between': #e.g., length:>600 or length:<=600 or "length" : "between 200 AND 2000"
                where_clause = where_clause + " AND podcast_episode_length {}".format(inputDict["length"])
            else: #e.g., length:600
                where_clause = where_clause + " AND podcast_episode_length = {}".format(inputDict["length"])
        if  "genre" in inputDict:
            where_clause =  where_clause + " AND mediame.md_type_id = 6 AND mediamd.md_value = '{}'".format(inputDict["genre"]) #genre id = 6 for podcast

        final_sql = sql_template_podcastep + where_clause + endclause


    elif inputDict["mediaType"] == "podcast":
        if "name" in inputDict:
            where_clause = where_clause + " AND lower(podcast_title) = '{}'".format(inputDict["name"].lower())
        if "date" in inputDict:
            if inputDict["date"][0] == '>' or inputDict['date'][0] == '<': #e.g., date:>2017-01-01
                where_clause = where_clause + " AND podcast_last_updated {} '{}'".format(inputDict["date"][0], inputDict["date"][1:])
            elif inputDict["date"][0:2] == '>=' or inputDict['date'][0:2] == '<=': #e.g., publish_date:>=2017-01-01
                where_clause = where_clause + " AND podcast_last_updated {} '{}'".format(inputDict["date"][0:2], inputDict["date"][2:])
            elif inputDict["date"].split()[0].lower() == 'between': 
                where_clause = where_clause + " AND podcast_last_updated BETWEEN '{}' AND '{}'".format(inputDict["date"].split()[1], inputDict["date"].split()[3])
            else: #e.g., publish_date:2018-01-11
                where_clause = where_clause + " AND podcast_last_updated = '{}'".format(inputDict["date"])
        if  "genre" in inputDict:
            where_clause =  where_clause + " AND p_to_md.md_type_id = 6 AND p_to_md.md_value = '{}'".format(inputDict["genre"])

        final_sql = sql_template_podcast + where_clause + endclause

    elif inputDict["mediaType"] == "all":
        where_clause_podcast = " WHERE true"
        where_clause_podcastep = " WHERE true"

        if  "genre" in inputDict:
            where_clause_podcast = where_clause_podcast + " AND p_to_md.md_type_id = 6 AND p_to_md.md_value = '{}'".format(inputDict["genre"])
            where_clause_podcastep = where_clause_podcastep + " AND mediame.md_type_id = 6 AND mediamd.md_value = '{}'".format(inputDict["genre"])

        if "date" in inputDict:
            if inputDict["date"][0] == '>' or inputDict['date'][0] == '<': #e.g., publish_date:>2017-01-01
                where_clause_podcastep = where_clause_podcastep + " AND podcast_episode_published_date {} '{}'".format(inputDict["date"][0], inputDict["date"][1:])
                where_clause_podcast = where_clause_podcast + " AND podcast_last_updated {} '{}'".format(inputDict["date"][0], inputDict["date"][1:])

            elif inputDict["date"][0:2] == '>=' or inputDict['date'][0:2] == '<=': #e.g., publish_date:>=2017-01-01
                where_clause_podcastep = where_clause_podcastep + " AND podcast_episode_published_date {} '{}'".format(inputDict["date"][0:2], inputDict["date"][2:])
                where_clause_podcast = where_clause_podcast + " AND podcast_last_updated {} '{}'".format(inputDict["date"][0:2], inputDict["date"][2:])


            elif inputDict["date"].split()[0].lower() == 'between': 
                where_clause_podcastep = where_clause_podcastep + " AND podcast_episode_published_date BETWEEN '{}' AND '{}'".format(inputDict["date"].split()[1], inputDict["date"].split()[3])
                where_clause_podcast = where_clause_podcast + " AND podcast_last_updated BETWEEN '{}' AND '{}'".format(inputDict["date"].split()[1], inputDict["date"].split()[3])
            
            else: #e.g., publish_date:2018-01-11
                where_clause_podcastep = where_clause_podcastep + " AND podcast_episode_published_date = '{}'".format(inputDict["date"])
                where_clause_podcast = where_clause_podcast + " AND podcast_last_updated = '{}'".format(inputDict["date"])

        if "length" in inputDict:
            if inputDict["length"][0] == '>' or inputDict["length"][0] == '<' or inputDict["length"].split()[0].lower() == 'between': #e.g., length:>600 or length:<=600 or "length" : "between 200 AND 2000"
                where_clause_podcastep = where_clause_podcastep + " AND podcast_episode_length {}".format(inputDict["length"])
            else: #e.g., length:600
                where_clause_podcastep = where_clause_podcastep + " AND podcast_episode_length = {}".format(inputDict["length"])
        
        if "name" in inputDict:
            where_clause_podcastep = where_clause_podcastep + " AND lower(podcast_episode_title) = '{}'".format(inputDict["name"].lower())
            where_clause_podcast = where_clause_podcast + " AND lower(podcast_title) = '{}'".format(inputDict["name"].lower())
            
            
            
        final_sql = "((" + sql_template_podcastep + where_clause_podcastep +")"+ " UNION " + "(" + sql_template_podcast + where_clause_podcast +")) " + endclause

     


    try:
        r = dictfetchall(cur,final_sql)
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Error Couldn't Search for the podcast episode in Advanced Search")
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return None




def search_song_or_album_genre_multi(inDict):
    """
    Searches for matching song genre contents by given filters
    Input Examples-> 
    1. mediaType:song ,name:You Are In Love
    2. mediaType:song ,name:You Are In Love,genre : pop
    3. mediaType:song, artist:Bon Jovi
    4. mediaType:song, artist:Bon Jovi, length: >100
    4. mediaType:song, artist:Bon Jovi, length: >300
    2. mediaType:all, genre: pop
    3. mediaType:album, name:JESUS IS KING
    4. mediaType:album, artist:Bon Jovi
    4. mediaType:all ,genre:pop
    5. mediaType:all, artist:Bon Jovi
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        sql_template_song = """SELECT S.song_id as item_id, S.song_title as item_title, 'Song' as item_type
                                FROM mediaserver.song S LEFT OUTER JOIN mediaserver.mediaitemmetadata mimd on (S.song_id = mimd.media_id)
                                join mediaserver.Metadata md on (mimd.md_id = md.md_id)
                                join mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)
                                join mediaserver.song_artists SA on (S.song_id = SA.song_id)
                                join mediaserver.artist A on (SA.performing_artist_id = A.artist_id)
                                """

        
        sql_template_album = """SELECT AL.album_id as item_id, AL.album_title as item_title, 'Album' as item_type
                                FROM mediaserver.album AL LEFT OUTER JOIN mediaserver.mediaitemmetadata mimd on (AL.album_id = mimd.media_id)
                                join mediaserver.Metadata md on (mimd.md_id = md.md_id)
                                join mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)
                                natural join mediaserver.album_songs ALS 
                                natural join mediaserver.song_artists SA 
                                join mediaserver.artist A on (SA.performing_artist_id = A.artist_id) """
        

        sql_ending = """ group by item_id, item_title, item_type
                            order by  item_id"""

        
        where_clause = " WHERE md.md_type_id = 1 "        

       
        if inDict["mediaType"] == "song":
            if "name" in inDict:
                where_clause += " AND " + "S.song_title = '{}' ".format(inDict["name"])

            if "genre" in inDict:
                where_clause += " AND " + "md.md_value = '{}' ".format(inDict["genre"])
                
            
            if "artist" in inDict:
                where_clause += " AND " + "A.artist_name = '{}' ".format(inDict["artist"])
            if "length" in inDict:
                where_clause += " AND " + "S.length  {} ".format(inDict["length"])

            final_sql = sql_template_song + where_clause + sql_ending


        elif inDict["mediaType"] == "album":
            where_clause = " "
            if "name" in inDict:
                where_clause += " AND " + "AL.album_title = '{}' ".format(inDict["name"])
                print(where_clause)

            if "genre" in inDict:
                where_clause += " AND " + "md.md_value = '{}' ".format(inDict["genre"])
            
            if "artist" in inDict:
                where_clause += " AND " + "A.artist_name = '{}' ".format(inDict["artist"])
            
            final_sql = sql_template_album + where_clause + sql_ending

        
        elif inDict["mediaType"] == "all":
            where_clause_song = ""
            where_clause_album = ""
            
            if  "genre" in inDict:
                where_clause = where_clause + " AND " +  "md.md_value = '{}' ".format(inDict["genre"])
            
            if "name" in inDict:
                where_clause_song += where_clause + " AND " + "S.song_title = '{}'".format(inDict["name"])

                where_clause_album += where_clause_album + " AND " + "AL.album_title = '{}'".format(inDict["name"])

            if "artist" in inDict:
                where_clause_song += " AND " + "A.artist_name = '{}' ".format(inDict["artist"])

                where_clause_album += " AND " + "A.artist_name = '{}' ".format(inDict["artist"])

            
            final_sql = "(" + sql_template_song + where_clause_song + ")" + " UNION " + "(" +  sql_template_album + where_clause_album + ")"
    

        r = dictfetchall(cur,final_sql)
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Error Couldn't Search for the Song/Album in Advanced Search")

    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None





#####################################################
#   Query (1)
#   Login
#####################################################

def check_login(username, password):
    """
    Check that the users information exists in the database.
        - True => return the user data
        - False => return None
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        #############################################################################
        # Fill in the SQL below in a manner similar to Wk 08 Lab to log the user in #
        #############################################################################

        sql = """
        select username from mediaserver.useraccount

        where username = %s and password = %s;
        """

        print(username)
        print(password)

        r = dictfetchone(cur,sql,(username,password))
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Error Invalid Login")
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Is Superuser? - 
#   is this required? we can get this from the login information
#####################################################

def is_superuser(username):
    """
    Check if the user is a superuser.
        - True => Get the departments as a list.
        - False => Return None
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """SELECT isSuper
                 FROM mediaserver.useraccount
                 WHERE username=%s AND isSuper;"""
        print("username is: "+username)
        cur.execute(sql, (username))
        r = cur.fetchone()              # Fetch the first row
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (1 b)
#   Get user playlists
#####################################################
def user_playlists(username):
    """
    Check if user has any playlists
        - True -> Return all user playlists
        - False -> Return None
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        ###############################################################################
        # Fill in the SQL below and make sure you get all the playlists for this user #
        ###############################################################################
        sql = """SELECT MC.collection_id, MC.collection_name, count(*) as count
                FROM mediaserver.useraccount UA NATURAL JOIN mediaserver.MediaCollection MC NATURAL JOIN 
                mediaserver.MediaCollectionContents MCC
                WHERE UA.username = %s
                GROUP BY MC.collection_id, MC.collection_name
                ORDER BY MC.collection_id desc;"""

        print("username is: "+username)
        r = dictfetchall(cur,sql,(username,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting User Playlists:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (1 a)
#   Get user podcasts
#####################################################
def user_podcast_subscriptions(username):
    """
    Get user podcast subscriptions.
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        #################################################################################
        # Fill in the SQL below and get all the podcasts that the user is subscribed to #
        #################################################################################

        sql = """ SELECT P.podcast_id,P.podcast_title,P.podcast_uri,P.podcast_last_updated
            FROM mediaserver.useraccount UA NATURAL JOIN mediaserver.Subscribed_Podcasts SP
                NATURAL JOIN mediaserver.Podcast P
            WHERE UA.username = %s;"""


        r = dictfetchall(cur,sql,(username,))
        print("return val is:")
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Podcast subs:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (1 c)
#   Get user in progress items
#####################################################
def user_in_progress_items(username):
    """
    Get user in progress items that aren't 100%
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:


        ###################################################################################
        # Fill in the SQL below with a way to find all the in progress items for the user #
        ###################################################################################

        sql = """
        select UMC.media_id,UMC.play_count as playcount ,UMC.progress,UMC.lastviewed ,storage_location
        from mediaserver.useraccount UA 
                natural join mediaserver.UserMediaConsumption UMC
                natural join mediaserver.MediaItem MI
        where username = %s and progress != 100
        order by UMC.lastviewed desc;

        """


        r = dictfetchall(cur,sql,(username,))
        print("Given username is {} and return val is:".format(username))
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting User Consumption - Likely no values:", sys.exc_info()[0])
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Get all artists
#####################################################
def get_allartists():
    """
    Get all the artists in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select 
            a.artist_id, a.artist_name, count(amd.md_id) as count
        from 
            mediaserver.artist a left outer join mediaserver.artistmetadata amd on (a.artist_id=amd.artist_id)
        group by a.artist_id, a.artist_name
        order by a.artist_name;"""

        r = dictfetchall(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Artists:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None
#####################################################
#   Additional Function
#   Get song genres
#####################################################
def get_song_genres():
    """
    Get the meta for a song by their ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """SELECT * 
        FROM mediaserver.metadatatype 
            natural join mediaserver.metadata 
        where md_type_name = 'song genre';"""

        r = dictfetchall(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting all song genres: ", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Get all songs
#####################################################
def get_allsongs():
    """
    Get all the songs in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select 
            s.song_id, s.song_title, string_agg(saa.artist_name,',') as artists
        from 
            mediaserver.song s left outer join 
            (mediaserver.Song_Artists sa join mediaserver.Artist a on (sa.performing_artist_id=a.artist_id)
            ) as saa  on (s.song_id=saa.song_id)
        group by s.song_id, s.song_title
        order by s.song_id;"""

        r = dictfetchall(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Songs:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Get all podcasts
#####################################################
def get_allpodcasts():
    """
    Get all the podcasts in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select 
                p.*, pnew.count as count  
            from 
                mediaserver.podcast p, 
                (select 
                    p1.podcast_id, count(*) as count 
                from 
                    mediaserver.podcast p1 left outer join mediaserver.podcastepisode pe1 on (p1.podcast_id=pe1.podcast_id) 
                    group by p1.podcast_id) pnew 
            where p.podcast_id = pnew.podcast_id;"""

        r = dictfetchall(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Podcasts:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None



#####################################################
#   Get all albums
#####################################################
def get_allalbums():
    """
    Get all the Albums in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select 
                a.album_id, a.album_title, anew.count as count, anew.artists
            from 
                mediaserver.album a, 
                (select 
                    a1.album_id, count(distinct as1.song_id) as count, array_to_string(array_agg(distinct ar1.artist_name),',') as artists
                from 
                    mediaserver.album a1 
			left outer join mediaserver.album_songs as1 on (a1.album_id=as1.album_id) 
			left outer join mediaserver.song s1 on (as1.song_id=s1.song_id)
			left outer join mediaserver.Song_Artists sa1 on (s1.song_id=sa1.song_id)
			left outer join mediaserver.artist ar1 on (sa1.performing_artist_id=ar1.artist_id)
                group by a1.album_id) anew 
            where a.album_id = anew.album_id;"""

        r = dictfetchall(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Albums:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None



#####################################################
#   Query (3 a,b c)
#   Get all tvshows
#####################################################
def get_alltvshows():
    """
    Get all the TV Shows in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        #############################################################################
        # Fill in the SQL below with a query to get all tv shows and episode counts #
        #############################################################################
        # Changing names have to be reflected on html
        sql = """SELECT T.tvshow_id, T.tvshow_title as tvshow_title, TVS_Ep.count as count 
               FROM mediaserver.tvshow T, ( SELECT TS.tvshow_id, COUNT(TVE.media_id) as count
                                                FROM mediaserver.tvshow TS 
                                                    left outer join mediaserver.TVEpisode TVE on (TS.tvshow_id=TVE.tvshow_id) 
                                                GROUP BY TS.tvshow_id) as TVS_Ep        
                WHERE T.tvshow_id = TVS_Ep.tvshow_id
                ORDER BY T.tvshow_id;"""

        r = dictfetchall(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All TV Shows:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Get all movies
#####################################################
def get_allmovies():
    """
    Get all the Movies in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select 
            m.movie_id, m.movie_title, m.release_year, count(mimd.md_id) as count
        from 
            mediaserver.movie m left outer join mediaserver.mediaitemmetadata mimd on (m.movie_id = mimd.media_id)
        group by m.movie_id, m.movie_title, m.release_year
        order by movie_id;"""

        r = dictfetchall(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Movies:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Get one artist
#####################################################
def get_artist(artist_id):
    """
    Get an artist by their ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select *
        from mediaserver.artist a left outer join 
            (mediaserver.artistmetadata natural join mediaserver.metadata natural join mediaserver.MetaDataType) amd
        on (a.artist_id=amd.artist_id)
        where a.artist_id=%s;"""

        r = dictfetchall(cur,sql,(artist_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Artist with ID: '"+artist_id+"'", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None
#####################################################
#   Additonal Function for single song to have album artwork
#   
#####################################################
def get_artist_description(artist_id):
    """
    Get an artist's descrption 
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select * from mediaserver.artist A natural join mediaserver.artistmetadata natural join mediaserver.metadata natural join mediaserver.metadatatype mdt
        where mdt.md_type_name = 'description' and A.artist_id=%s;"""

        r = dictfetchall(cur,sql,(artist_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Artist with ID: '"+artist_id+"'", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

def get_song_descripton(song_id):
    """
    Get a song's description by their ID in your media server

    
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        sql = """SELECT *
        FROM mediaserver.Album Album LEFT OUTER JOIN
        (mediaserver.AlbumMetaData NATURAL JOIN mediaserver.MetaData NATURAL JOIN mediaserver.MetaDataType) Album_to_MetaData
		ON (Album.album_id = Album_to_MetaData.album_id)
		LEFT OUTER JOIN mediaserver.album_songs albS on (Album.album_id=albS.album_id) 
        LEFT OUTER JOIN mediaserver.song S on (albS.song_id=S.song_id)
 		where md_type_name = 'description' and S.song_id = %s;"""

        r = dictfetchall(cur,sql,(song_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Get a song's album artwork :", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

    

    


def get_song_artwork(song_id):
    """
    Get a song's album artwork by their ID in your media server

    
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        sql = """SELECT Album.album_title, md_type_name, md_value
        FROM mediaserver.Album Album LEFT OUTER JOIN
        (mediaserver.AlbumMetaData NATURAL JOIN mediaserver.MetaData NATURAL JOIN mediaserver.MetaDataType) Album_to_MetaData
		ON (Album.album_id = Album_to_MetaData.album_id)
		LEFT OUTER JOIN mediaserver.album_songs albS on (Album.album_id=albS.album_id) 
        LEFT OUTER JOIN mediaserver.song S on (albS.song_id=S.song_id)
        
         WHERE S.song_id = %s;"""

        r = dictfetchall(cur,sql,(song_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Get a song's album artwork :", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None
#####################################################
#   Query (2 a,b,c)
#   Get one song
#####################################################
def get_song(song_id):
    """
    Get a song by their ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        #############################################################################
        # Fill in the SQL below with a query to get all information about a song    #
        # and the artists that performed it                                         #
        #############################################################################
        sql = """SELECT S.song_id, S.song_title, S.length, string_agg(song_To_Artist.artist_name,',') as performed_artists
                FROM mediaserver.song S LEFT OUTER JOIN 
                (mediaserver.Song_Artists SA join mediaserver.Artist A on (SA.performing_artist_id = A.artist_id)
                ) as song_To_Artist  on (S.song_id = song_To_Artist.song_id)
                WHERE S.song_id = %s
                GROUP BY S.song_id, S.song_title, S.length
                ORDER BY S.song_id;"""

        r = dictfetchall(cur,sql,(song_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Songs:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (2 d)
#   Get metadata for one song
#####################################################
def get_song_metadata(song_id):
    """
    Get the meta for a song by their ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        #############################################################################
        # Fill in the SQL below with a query to get all metadata about a song       #
        #############################################################################

        sql = """
        select md_type_id, md_id, md_value, md_type_name 
        from mediaserver.song S LEFT OUTER JOIN
        (mediaserver.mediaitemmetadata NATURAL JOIN mediaserver.metadata NATURAL JOIN mediaserver.MetaDataType) s_to_md
        on (S.song_id = s_to_md.media_id)
        WHERE S.song_id=%s;

        """


        r = dictfetchall(cur,sql,(song_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting song metadata for ID: "+song_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (6 a,b,c,d,e)
#   Get one podcast and return all metadata associated with it
#####################################################
def get_podcast(podcast_id):
    """
    Get a podcast by their ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:


        #############################################################################
        # Fill in the SQL below with a query to get all information about a podcast #
        # including all metadata associated with it                                 #
        #############################################################################
        sql = """
        SELECT *
        FROM mediaserver.podcast pod LEFT OUTER JOIN 
            (mediaserver.podcastmetadata NATURAL JOIN mediaserver.metadata NATURAL JOIN mediaserver.metadatatype) p_to_md 
            ON (pod.podcast_id = p_to_md.podcast_id)
        WHERE pod.podcast_id = %s;
        """



        r = dictfetchall(cur,sql,(podcast_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Podcast with ID: "+podcast_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (6 f)
#   Get all podcast eps for one podcast
#####################################################
def get_all_podcasteps_for_podcast(podcast_id):
    """
    Get all podcast eps for one podcast by their podcast ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
 
        #############################################################################
        # Fill in the SQL below with a query to get all information about all       #
        # podcast episodes in a podcast                                             #
        #############################################################################
        
        sql = """
        SELECT *
        FROM mediaserver.podcastepisode
        WHERE podcast_id = %s
        ORDER BY podcast_episode_published_date DESC;
        """
        

        r = dictfetchall(cur,sql,(podcast_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Podcast Episodes for Podcast with ID: "+podcast_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Query (7 a,b,c,d,e,f)
#   Get one podcast ep and associated metadata
#####################################################
def get_podcastep(podcastep_id):
    """
    Get a podcast ep by their ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:


        #############################################################################
        # Fill in the SQL below with a query to get all information about a         #
        # podcast episodes and it's associated metadata                             #
        #############################################################################
        sql = """
        SELECT podep.media_id, podcast_episode_title, podcast_episode_uri, podcast_episode_published_date, podcast_episode_length, md_type_name, md_value
        FROM mediaserver.podcastepisode podep LEFT OUTER JOIN 
            (mediaserver.mediaitemmetadata NATURAL JOIN mediaserver.metadata NATURAL JOIN mediaserver.metadatatype) mediamd 
            ON (podep.media_id = mediamd.media_id)
        WHERE podep.media_id = %s;
        """


        r = dictfetchall(cur,sql,(podcastep_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Podcast Episode with ID: "+podcastep_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Query (5 a,b)
#   Get one album
#####################################################
def get_album(album_id):
    """
    Get an album by their ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        #############################################################################
        # Fill in the SQL below with a query to get all information about an album  #
        # including all relevant metadata                                           #
        #############################################################################
        sql = """SELECT Album.album_title, md_type_name, md_value
        FROM mediaserver.Album Album LEFT OUTER JOIN
        (mediaserver.AlbumMetaData NATURAL JOIN mediaserver.MetaData NATURAL JOIN mediaserver.MetaDataType) Album_to_MetaData
        ON (Album.album_id = Album_to_MetaData.album_id)
        WHERE Album.album_id = %s;
        """

        r = dictfetchall(cur,sql,(album_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Albums with ID: "+album_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Query (5 d)
#   Get all songs for one album
#####################################################
def get_album_songs(album_id):
    """
    Get all songs for an album by the album ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        #############################################################################
        # Fill in the SQL below with a query to get all information about all       #
        # songs in an album, including their artists                                #
        #############################################################################

        sql = """  SELECT S.song_id, S.song_title, array_to_string(array_agg(DISTINCT A.artist_name),',') as artists
        FROM mediaserver.album Alb
            LEFT OUTER JOIN mediaserver.album_songs albS on (Alb.album_id=albS.album_id) 
            LEFT OUTER JOIN mediaserver.song S on (albS.song_id=S.song_id)
            LEFT OUTER JOIN mediaserver.Song_Artists SA on (S.song_id=SA.song_id)
            LEFT OUTER JOIN mediaserver.artist A on (SA.performing_artist_id = A.artist_id)
        WHERE Alb.album_id = %s
        GROUP BY S.song_id, albS.track_num
        ORDER BY albS.track_num;
        """
        r = dictfetchall(cur,sql,(album_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Albums songs with ID: "+album_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Query (5 c)
#   Get all genres for one album
#####################################################
def get_album_genres(album_id):
    """
    Get all genres for an album by the album ID in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:


        #############################################################################
        # Fill in the SQL below with a query to get all information about all       #
        # genres in an album (based on all the genres of the songs in that album)   #
        #############################################################################
# remove string_agg
        sql =  """	           SELECT DISTINCT M.md_value as songgenres, M.md_id as songgenresid
                FROM mediaserver.album A
                        LEFT OUTER JOIN mediaserver.album_songs albS on (A.album_id=albS.album_id) 
                        LEFT OUTER JOIN mediaserver.song S on (albS.song_id=S.song_id)
                        LEFT OUTER JOIN mediaserver.MediaItemMetadata MIMD on (S.song_id=MIMD.media_id)
                        JOIN mediaserver.Metadata M on (MIMD.md_id = M.md_id)
                        JOIN mediaserver.MetadataType MT on (M.md_type_id=MT.md_type_id)
                WHERE A.album_id=%s and md_type_name = 'song genre'
                
            """
        r = dictfetchall(cur,sql,(album_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Albums genres with ID: "+album_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

def get_album_descriptions(album_id):

    """
    Get all descriptions for songs in album
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:


        
        sql =  """	           SELECT *
        FROM mediaserver.Album Album LEFT OUTER JOIN
        (mediaserver.AlbumMetaData NATURAL JOIN mediaserver.MetaData NATURAL JOIN mediaserver.MetaDataType) Album_to_MetaData
		ON (Album.album_id = Album_to_MetaData.album_id)
		LEFT OUTER JOIN mediaserver.album_songs albS on (Album.album_id=albS.album_id) 
        LEFT OUTER JOIN mediaserver.song S on (albS.song_id=S.song_id)
        WHERE Album.album_id=%s and md_type_name = 'description';
        """
        r = dictfetchall(cur,sql,(album_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Albums genres with ID: "+album_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None





#####################################################
#   Query (10)
#   May require the addition of SQL to multiple 
#   functions and the creation of a new function to
#   determine what type of genre is being provided
#   You may have to look at the hard coded values
#   in the sampledata to make your choices

# Query 10 - Additonal Function - Type of Genre
#####################################################
def get_genre_type(genre_id):
    """
    Get Type of Genre i.e. Song,Film etc
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:


        #############################################################################
        # Fill in the SQL below with a query to get Genre type                      #
        #############################################################################
        sql = """       select md_type_name 
                        from mediaserver.metadatatype 
                        natural join mediaserver.metadata
			            where md_id = %s
			            LIMIT 1;      """

        r = dictfetchall(cur,sql,(genre_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Type of Genre with Genre id (md_id): ", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None
#####################################################
#   Query (10)
#   Get all songs for one song_genre
#####################################################
def get_genre_songs(genre_id):
    """
    Get all songs for a particular song_genre ID in your media server
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        #########
        # TODO  #  
        #########

        #############################################################################
        # Fill in the SQL below with a query to get all information about all       #
        # songs which belong to a particular genre_id                               #
        #############################################################################
        sql = """
                SELECT S.song_id as item_id, S.song_title as item_title, 'Song' as item_type
                FROM mediaserver.song S LEFT OUTER JOIN mediaserver.mediaitemmetadata mimd on (S.song_id = mimd.media_id)
                    JOIN mediaserver.Metadata md on (mimd.md_id = md.md_id)
                    JOIN mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)
                WHERE md.md_type_id = 1 AND md.md_id = %s
				GROUP BY S.song_id, S.song_title,item_type
                ORDER BY S.song_id;
        """

        r = dictfetchall(cur,sql,(genre_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Songs with Genre ID: "+genre_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (10) - Rahul Talla - DONE
#   Get all podcasts for one podcast_genre
#####################################################
def get_genre_podcasts(genre_id):
    """
    Get all podcasts for a particular podcast_genre ID in your media server
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
 

        #############################################################################
        # Fill in the SQL below with a query to get all information about all       #
        # podcasts which belong to a particular genre_id                            #
        #############################################################################
        sql = """
                /*SELECT P.podcast_id as item_id, P.podcast_title as item_title, 'Podcast' as item_type
                FROM mediaserver.podcast P left outer join mediaserver.PodcastEpisode PE on (P.podcast_id = PE.podcast_id)
                    JOIN mediaserver.mediaitemmetadata mimd on (PE.podcast_id = mimd.media_id)
                    JOIN mediaserver.Metadata md on (mimd.md_id = md.md_id)
                    JOIN mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)
                WHERE md.md_type_id = 6 AND md.md_id = [CHANGE]
				GROUP BY P.podcast_id, P.podcast_title,item_type
                ORDER BY P.podcast_id;*/

                SELECT P.podcast_id as item_id, P.podcast_title as item_title, 'Podcast' as item_type
                FROM mediaserver.podcast P left outer join mediaserver.PodcastEpisode PE on (P.podcast_id = PE.podcast_id)
					JOIN mediaserver.PodcastMetadata pm on (P.podcast_id = pm.podcast_id)
                    JOIN mediaserver.Metadata md on (pm.md_id = md.md_id)
                    JOIN mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)
					WHERE md.md_type_id = 6 AND pm.md_id = %s
                    GROUP BY P.podcast_id, P.podcast_title,item_type,md_type_name
                	ORDER BY P.podcast_id;
        """

        r = dictfetchall(cur,sql,(genre_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting Podcasts with Genre ID: "+ genre_id, sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Query (10) - Rahul Talla - DONE
#   Get all movies and tv shows for one film_genre
#####################################################
def get_genre_movies_and_shows(genre_id):
    """
    Get all movies and tv shows for a particular film_genre ID in your media server
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
                
        sql ="""(SELECT M.movie_id as item_id, M.movie_title as item_title, 'Movie' as item_type
                FROM mediaserver.movie M LEFT OUTER JOIN mediaserver.mediaitemmetadata mimd on (m.movie_id = mimd.media_id)
                    JOIN mediaserver.Metadata md on (mimd.md_id = md.md_id)
                    JOIN mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)
                WHERE md.md_type_id = 2 AND md.md_id = {}
                ORDER BY M.movie_id)
                
                UNION 

                (SELECT T.tvshow_id as item_id, T.tvshow_title as item_title, 'TV Show' as item_type
                FROM mediaserver.tvshow T left outer join mediaserver.TVEpisode TE on (T.tvshow_id = TE.tvshow_id)
                    JOIN mediaserver.TVShowMetaData  TVMD on (TE.tvshow_id = TVMD.tvshow_id)
                    JOIN mediaserver.Metadata md on (TVMD.md_id = md.md_id)
                    JOIN mediaserver.MetadataType mdt on (md.md_type_id = mdt.md_type_id)
                WHERE md.md_type_id = 2 AND TVMD.md_id = {}
				GROUP BY T.tvshow_id, T.tvshow_title,item_type
                ORDER BY T.tvshow_id)
                """.format(genre_id,genre_id)

        res = dictfetchall(cur,sql)

        print("Returned: {}".format(res))
        
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return res
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Movies and TV Shows by Genre:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    
    return None



#####################################################
#   Query (4 a,b)
#   Get one tvshow
#####################################################
def get_tvshow(tvshow_id):
    """
    Get one tvshow in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:

        #############################################################################
        # Fill in the SQL below with a query to get all information about a tv show #
        # including all relevant metadata       #
        #############################################################################
        sql = """SELECT tvshow_title, md_type_name, md_value,md_id
        FROM mediaserver.TVShow T LEFT OUTER JOIN
        (mediaserver.TVShowMetaData NATURAL JOIN mediaserver.MetaData NATURAL JOIN mediaserver.MetaDataType) TVShow_to_MetaData
        ON (T.tvshow_id = TVShow_to_MetaData.tvshow_id)
        WHERE T.tvshow_id = %s;
        """
        r = dictfetchall(cur,sql,(tvshow_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All TV Shows:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Query (4 c)
#   Get all tv show episodes for one tv show
#####################################################
def get_all_tvshoweps_for_tvshow(tvshow_id):
    """
    Get all tvshow episodes for one tv show in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
 
        #############################################################################
        # Fill in the SQL below with a query to get all information about all       #
        # tv episodes in a tv show                                                  #
        #############################################################################
        sql = """SELECT *
        FROM mediaserver.TVEpisode
        WHERE tvshow_id = %s
        ORDER BY season, episode;
        """

        r = dictfetchall(cur,sql,(tvshow_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All TV Shows:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Get one tvshow episode
#####################################################
def get_tvshowep(tvshowep_id):
    """
    Get one tvshow episode in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select * 
        from mediaserver.TVEpisode te left outer join 
            (mediaserver.mediaitemmetadata natural join mediaserver.metadata natural join mediaserver.MetaDataType) temd
            on (te.media_id=temd.media_id)
        where te.media_id = %s"""

        r = dictfetchall(cur,sql,(tvshowep_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All TV Shows:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################

#   Get one movie
#####################################################
def get_movie(movie_id):
    """
    Get one movie in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """select *
        from mediaserver.movie m left outer join 
            (mediaserver.mediaitemmetadata natural join mediaserver.metadata natural join mediaserver.MetaDataType) mmd
        on (m.movie_id=mmd.media_id)
        where m.movie_id=%s;"""

        r = dictfetchall(cur,sql,(movie_id,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All Movies:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Find all matching tvshows
#####################################################
def find_matchingtvshows(searchterm):
    """
    Get all the matching TV Shows in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """
            select 
                t.*, tnew.count as count  
            from 
                mediaserver.tvshow t, 
                (select 
                    t1.tvshow_id, count(te1.media_id) as count 
                from 
                    mediaserver.tvshow t1 left outer join mediaserver.TVEpisode te1 on (t1.tvshow_id=te1.tvshow_id) 
                    group by t1.tvshow_id) tnew 
            where t.tvshow_id = tnew.tvshow_id and lower(tvshow_title) ~ lower(%s)
            order by t.tvshow_id;"""

        r = dictfetchall(cur,sql,(searchterm,))
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error getting All TV Shows:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None

#####################################################
#   Find all matching songs
#####################################################



#####################################################
#   Query (9) - Rahul Talla - DONE
#   Find all matching Movies
#####################################################
def find_matchingmovies(searchterm):
    """
    Get all the matching Movies in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
                
        sql ="""SELECT M.movie_id, M.movie_title, M.release_year, COUNT(mimd.md_id) as count
                FROM mediaserver.movie M LEFT OUTER JOIN mediaserver.mediaitemmetadata mimd on (m.movie_id = mimd.media_id)
                WHERE LOWER(M.movie_title) LIKE LOWER(%s)
                GROUP BY M.movie_id, M.movie_title, M.release_year
                ORDER BY M.movie_id;"""

        res = dictfetchall(cur,sql,(searchterm,))

        print("Returned: {}".format(res))
        
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return res
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error finding all movies:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    
    return None



#####################################################
#   Add a new Movie
#####################################################
def add_movie_to_db(title,release_year,description,storage_location,genre):
    """
    Add a new Movie to your media server
    """
    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """
        SELECT 
            mediaserver.addMovie(
                %s,%s,%s,%s,%s);
        """

        cur.execute(sql,(storage_location,description,title,release_year,genre))
        conn.commit()                   # Commit the transaction
        r = cur.fetchone()
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error adding a movie:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#####################################################
#   Most Recent SongAdded (Query 8) - Additonal Function 
#   To check correct adding of song
#####################################################
def  recent_songs_top5():
    """
    Most Recent SongAdded  top 5
    """

    # Check database is connected

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()

    try: 

        # Add song with builtin Function 
        query = """ SELECT *  FROM mediaserver.song order by song_id DESC LIMIT 5;"""

        #  Printing SQL to be inserted 
        print_sql_string(query,(title,description,artist_id,song_len,storage_loc,genre))
        cur.execute(query,(title,description,artist_id,song_len,storage_loc,genre))
        conn.commit()
        res = cur.fetchone()

        print(" Most Recent Songs Added Top 5: {}".format(res)) # Prints TOP 5 Songs in terminal
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error retrieving songs in db:", sys.exc_info()[0])
        raise

    return None

#####################################################
#   Query (8) - Rahul Talla - DONE
#   Add a new Song
#####################################################
def add_song_to_db(song_params):
    """
    Get all the matching Movies in your media server
    """
    title = song_params['song_title']
    description = song_params['description']
    artist_id = song_params['artist_id']
    song_len = song_params['song_length']
    storage_loc = song_params['storage_location']
    genre = song_params['song_genre']

    # Check database is connected

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()

    try: 

        # Add song with builtin Function 
        query = """ SELECT mediaserver.addSong(%s,%s,%s,%s,%s,%s);"""

        #  Printing SQL to be inserted 
        print_sql_string(query,(title,storage_loc, genre, description,artist_id,song_len))
        cur.execute(query,(title,storage_loc, genre, description,artist_id,song_len))
        conn.commit()
        res = cur.fetchone()

        print("Returned: {}".format(res))
        #print(recent_songs_top5())

        print()
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return res
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error adding a song to db:", sys.exc_info()[0])
        raise

    return None

#####################################################
#   Get last Movie
#####################################################
def get_last_movie():
    """
    Get all the latest entered movie in your media server
    """

    conn = database_connect()
    if(conn is None):
        return None
    cur = conn.cursor()
    try:
        # Try executing the SQL and get from the database
        sql = """
        select max(movie_id) as movie_id from mediaserver.movie"""

        r = dictfetchone(cur,sql)
        print("return val is:")
        print(r)
        cur.close()                     # Close the cursor
        conn.close()                    # Close the connection to the db
        return r
    except:
        # If there were any errors, return a NULL row printing an error to the debug
        print("Unexpected error adding a movie:", sys.exc_info()[0])
        raise
    cur.close()                     # Close the cursor
    conn.close()                    # Close the connection to the db
    return None


#  FOR MARKING PURPOSES ONLY
#  DO NOT CHANGE

def to_json(fn_name, ret_val):
    """
    TO_JSON used for marking; Gives the function name and the
    return value in JSON.
    """
    return {'function': fn_name, 'res': json.dumps(ret_val)}

# =================================================================
# =================================================================
