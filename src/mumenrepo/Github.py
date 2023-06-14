
from .common_imports import *

class Github(object):
    @staticmethod
    def official_endpoint(env):
        env.attr.github.endpoint = 'api.github.com'

    @staticmethod
    def base_header(env):
        env.github.request.headers = {'Accept': 'application/vnd.github.v3+json'}

    @staticmethod 
    def make_request(env, url, last_result=None):
        if last_result is not None and int(last_result.headers['X-RateLimit-Remaining']) <= 1:
            time_wait = float(last_result.headers['X-RateLimit-Reset']) - time.time() + 2.0
            if time_wait < 0:
                time.sleep( 120.0 )
            else:
                time.sleep( time_wait )
        return requests.get(url, headers=env.github.request.headers)

    @staticmethod
    def list_pull_requests(env):
        url = f'https://{env.attr.github.endpoint}/repos/{env.attr.github.owner}/{env.attr.github.repo}/pulls'
        return Github.make_request(env, url)

    @staticmethod
    def get_pull_request(env):
        url = f'https://{env.attr.github.endpoint}/repos/{env.attr.github.owner}/{env.attr.github.repo}/pulls/{env.attr.github.number}'
        return Github.make_request(env, url)

    @staticmethod
    def search_topic_default_params():
        return {"per_page":100, "sort":"stars"}

    @staticmethod
    def generate_topic_pages(env, total_counts, per_page=100):
        for i in range(1, 11):
            yield i
            if (i * per_page) > total_counts:
                break

    @staticmethod
    def search_topic(self, env, **kwargs):
        q = {'q': f"{kwargs['q']}+in:topics"}
        q.update(kwargs)
        qs = urllib.parse.urlencode(q)
        url = urllib.parse.quote(f"https://{env.attr.github.endpoint}/search/repositories?{qs}")
        return Github.make_request(env, url)

    @staticmethod
    def parse_datetime(s):
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").timestamp()

    @staticmethod
    def list_all_commits(env, existing_commits=None):
        newest_commit = None
        oldest_commit = None
        have_newest = False
        have_oldest = False
        commits = {}

        url_prefix = f'https://{env.attr.github.endpoint}/repos/{env.attr.github.owner}/{env.attr.github.repo}'

        def add_commits(new_commits):
            nonlocal newest_commit
            nonlocal oldest_commit
            for commit in new_commits:
                commits[ commit["sha"] ] = commit
                commit[ "time" ] = Github.parse_datetime( commit["commit"]["committer"]["date"] )

                if newest_commit is None:
                    newest_commit = oldest_commit = commit

                if commit[ "time" ] > newest_commit["time"]:
                    newest_commit = commit
                if commit[ "time" ] < oldest_commit["time"]:
                    oldest_commit = commit

        if existing_commits is None:
            existing_commits = {}

        if len(existing_commits) == 0:
            url = f'{url_prefix}/commits?per_page=100'
            more_commits = Github.make_request(env, url)
            if len(more_commits) == 0:
                raise Exception("no results on fresh listing")
            add_commits(more_commits)
        else:
            add_commits(existing_commits.values())

        while not have_newest or not have_oldest:
            if not have_newest:
                url = f'{url_prefix}/commits?per_page=100&since={newest_commit["commit"]["committer"]["date"]}'
                more_commits = Github.make_request(env, url)
                if len(more_commits) == 1:
                    if more_commits[0]["sha"] == newest_commit["sha"]:
                        have_newest = True
                elif len(more_commits) == 0:
                    have_newest = True
                add_commits(more_commits)
            if not have_oldest:
                url = f'{url_prefix}/commits?per_page=100&until={oldest_commit["commit"]["committer"]["date"]}'
                more_commits = Github.make_request(env, url)
                if len(more_commits) == 1:
                    if more_commits[0]["sha"] == oldest_commit["sha"]:
                        have_oldest = True
                elif len(more_commits) == 0:
                    have_oldest = True
                add_commits(more_commits)
            time.sleep(1.0)
        return commits

    @staticmethod
    def pull_request_buildable(env):
        env.attr.scheduler.event_name = f'{env.attr.pull.id}.build'
        pull_info = env.attr.pull.info
        build_result = Scheduler.get_result(env)

        if build_result is None or 'recent_build_sha' not in build_result:
            build = True
        elif build_result['recent_build_sha'] != pull_info['merge_commit_sha']:
            build = True
        else: 
            build = False

        return build