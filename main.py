import requests
import json
from datetime import datetime, timedelta
import humanize
#added a commenteedde
with open('config.json') as f:
    config_data = json.load(f)

date_from = config_data['from']
date_to = config_data['to']
usernames = config_data['users']
token = config_data['token']

queries_by_username = {}

for username in usernames:
    current_query = f'''
    {{
      user(login: "{username}") {{
        login,
        contributionsCollection(
          organizationID: "O_kgDOAvK6Lg" 
                                from: "{date_from}" 
                                to: "{date_to}"){{
          pullRequestReviewContributions(last: 100){{
            totalCount
            nodes{{
              occurredAt
              pullRequestReview{{
                author{{
                  login
                }}
                comments(last: 100){{
                  nodes{{
                    body
                    bodyText
                    state
                    author{{
                      login
                    }}
                  }}
                }}
                pullRequest{{
                  title
                  state
                  createdAt
                   author{{
                  login
                }}
                }}
                body
              }}
            }}
          }}
          pullRequestContributions(last: 100){{
            totalCount
            nodes{{
              occurredAt
              pullRequest{{
                title
                url
                state
                isDraft
                createdAt
                closedAt
                mergedAt
                author{{
                  login
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    '''

    queries_by_username[username] = current_query

url = f"https://api.github.com/graphql"

headers = {
    "Authorization": f"Bearer {token}"
}

responces_by_username = {}

for username, query in queries_by_username.items():

    r = requests.post(url, headers=headers, json={'query': query})

    if (r.status_code == 200):
        responces_by_username[username] = r.json()

user_infos = {}

for username, response in responces_by_username.items():

    user_info = {}
    
    pullRequestReviewContributions = response['data']['user']['contributionsCollection']['pullRequestReviewContributions']
    pullRequestContributions = response['data']['user']['contributionsCollection']['pullRequestContributions']

    total_reviews = pullRequestReviewContributions['totalCount']
    user_info['total_reviews'] = total_reviews

    collaborations = {}
    total_time_to_review = timedelta()
    max_time_to_review = timedelta()
    min_time_to_review = timedelta(days=365)
    total_comments = 0

    for pull_request_review in pullRequestReviewContributions['nodes']:
        reviewed_at = pull_request_review['occurredAt']
        all_comments = pull_request_review['pullRequestReview']['comments']['nodes']
        authored_comments = [comment for comment in all_comments if comment['author']['login'] == username]
        opened_at = pull_request_review['pullRequestReview']['pullRequest']['createdAt']
        pr_author = pull_request_review['pullRequestReview']['pullRequest']['author']['login']
        time_to_review = datetime.fromisoformat(reviewed_at) - datetime.fromisoformat(opened_at)

        time_to_review = datetime.fromisoformat(reviewed_at) - datetime.fromisoformat(opened_at)

        total_comments += len(authored_comments)

        total_time_to_review += time_to_review

        if (max_time_to_review < time_to_review):
            max_time_to_review = time_to_review

        if (min_time_to_review > time_to_review):
            min_time_to_review = time_to_review

        if pr_author in collaborations:
            collaborations[pr_author] += 1
        else:
            collaborations[pr_author] = 1

    user_info['total_pr_comments'] = total_comments
    user_info['average_pr_comments'] = total_comments / total_reviews
    user_info['collaborations'] = collaborations

    user_info['pr_average_time_to_review'] = humanize.precisedelta(total_time_to_review / total_reviews)

    user_info['pr_min_time_to_review'] = humanize.precisedelta(min_time_to_review)
    user_info['pr_max_time_to_review'] = humanize.precisedelta(max_time_to_review)

    total_pull_requests = pullRequestContributions['totalCount']
    user_info['total_pull_requests'] = total_pull_requests

    merged_pull_requests = sum(1 for pull_request in pullRequestContributions['nodes'] if pull_request['pullRequest']['state'] == 'MERGED')

    user_info['merged_pull_requests'] = merged_pull_requests

    total_time_to_close = timedelta()
    max_time_to_close = timedelta()
    min_time_to_close = timedelta(days=365)
    total_items_closed = 0

    for pull_request in pullRequestContributions['nodes']:
        created_at = pull_request['pullRequest']['createdAt']
        closed_at = pull_request['pullRequest']['closedAt']
        if (closed_at):
            total_items_closed += 1
            time_to_close = datetime.fromisoformat(closed_at) - datetime.fromisoformat(created_at)

            total_time_to_close += time_to_close

            if (max_time_to_close < time_to_close):
                max_time_to_close = time_to_close

            if (min_time_to_close > time_to_close):
                min_time_to_close = time_to_close

    if total_items_closed != 0:
        user_info['pr_average_time_to_close'] = humanize.precisedelta(total_time_to_close / total_items_closed)
    else:
        user_info['pr_average_time_to_close'] = 0

    user_info['pr_min_time_to_close'] = humanize.precisedelta(min_time_to_close)
    user_info['pr_max_time_to_close'] = humanize.precisedelta(max_time_to_close)

    user_infos[username] = user_info
        
print(json.dumps(user_infos))
