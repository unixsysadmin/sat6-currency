#!/usr/bin/python

import argparse
import json
import requests
import sys
import getpass
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


parser = argparse.ArgumentParser(description="Satellite 6 version of 'spacewalk-report system-currency'")
parser.add_argument("-a", "--advanced", action="store_true", default=False, help="Use this flag if you want to divide security errata by severity. Note: this will reduce performance of this script significantly.")
parser.add_argument("-n", "--server", type=str.lower, required=True, help="Satellite server (defaults to localhost)", default='localhost')
parser.add_argument("-u", "--username", type=str, required=True, help="Username to access Satellite")
parser.add_argument("-p", "--password", type=str, required=False, help="Password to access Satellite. The user will be asked interactively if password is not provided.")
parser.add_argument("-l", "--library", action="store_true", required=False, help="Use this flag to also report on Library Synced Content AND to divide security errata by severity. Note: this will reduce performance of this script significantly. Use with -o, -e and -c options")
parser.add_argument("-o", "--organization", type=str, required=False, help="Organization to use when using the '-l' option")
parser.add_argument("-c", "--contentview", type=str, required=False, default="Default Organization View", help="Content View to use using the '-l' option. Default: Default Organization View")
parser.add_argument("-e", "--environment", type=str, required=False, default="Library", help="Environment to use with the '-l' option. Default: Library")

args = parser.parse_args()

# Satellite specific parameters
url = "https://" + args.server
api = url + "/api/"
katello_api = url + "/katello/api/v2"
post_headers = {'content-type': 'application/json'}
ssl_verify=True

if args.password is None:
    args.password = getpass.getpass()

def get_with_json(location, json_data):
    """
    Performs a GET and passes the data to the url location
    """
    try:
        result = requests.get(location,
                            data=json_data,
                            auth=(args.username, args.password),
                            verify=ssl_verify,
                            headers=post_headers)

    except requests.ConnectionError, e:
        print sys.argv[0] + " Couldn't connect to the API, check connection or url"
        print e
        sys.exit(1)
    return result.json()

def simple_currency():

    # Print headline
    print "system_id,org_name,name,security,bug,enhancement,score,content_view,content_view_publish_date,lifecycle_environment,subscription_os_release,os_release,arch,subscription_status,comment"

    # Get all hosts (alter if you have more than 10000 hosts)
    hosts = get_with_json(api + "hosts", json.dumps({"per_page": "10000"}))["results"]

    # Multiply factors
    factor_sec = 8
    factor_bug = 2
    factor_enh = 1

    for host in hosts:
        # Check if host is registered with subscription-manager (unregistered hosts lack these values and are skipped)
        if "content_facet_attributes" in host and host["content_facet_attributes"]["errata_counts"]:

            # Get each number of different kinds of erratas
            errata_count_sec = host["content_facet_attributes"]["errata_counts"]["security"]
            errata_count_bug = host["content_facet_attributes"]["errata_counts"]["bugfix"]
            errata_count_enh = host["content_facet_attributes"]["errata_counts"]["enhancement"]
            content_view_name = host["content_facet_attributes"]["content_view"]["name"]
            content_view_id = host["content_facet_attributes"]["content_view"]["id"]
            lifecycle_environment = host["content_facet_attributes"]["lifecycle_environment"]["name"]
            lifecycle_environment_id = host["content_facet_attributes"]["lifecycle_environment"]["id"]
            subscription_os_release= host["subscription_facet_attributes"]["release_version"]
            arch = host["architecture_name"]
            subscription_status = host["subscription_status"]
            os_release = host["operatingsystem_name"]

            content_view = get_with_json(katello_api + "/content_views/" + str(content_view_id) + "/content_view_versions?environment_id=" + str(lifecycle_environment_id), json.dumps({"per_page": "10000"}))["results"]

            cv_date = content_view[0]["created_at"]
            if errata_count_sec is None or errata_count_bug is None or errata_count_enh is None:
                score = 0
            else:
            # Calculate weighted score
                score = errata_count_sec * factor_sec + errata_count_bug * factor_bug + errata_count_enh * factor_enh

            # Print result
            print str(host["id"]) + "," + str(host["organization_name"]) + "," + host["name"] + "," + str(errata_count_sec) + "," + str(errata_count_bug) + "," + str(errata_count_enh) + "," + str(score) + "," + str(content_view_name) + "," + str(cv_date) + "," + str(lifecycle_environment) + "," + str(subscription_os_release) + "," + str(os_release) + "," + str(arch) + "," + str(subscription_status) + "," + str(host["comment"])

def advanced_currency():

    # Print headline
    print "system_id,org_name,name,critical,important,moderate,low,bug,enhancement,score,content_view,content_view_publish_date,lifecycle_environment,subscription_os_release,os_release,arch,subscription_status,comment"

    # Get all hosts (if you have more than 10000 hosts, this method will take too long itme)
    hosts = get_with_json(api + "hosts", json.dumps({"per_page": "10000"}))["results"]

    # Multiply factors according to "spacewalk-report system-currency"
    factor_cri = 32
    factor_imp = 16
    factor_mod = 8
    factor_low = 4
    factor_bug = 2
    factor_enh = 1

    for host in hosts:

        # Get all errata for each host
        erratas = get_with_json(api + "hosts/" + str(host["id"]) + "/errata", json.dumps({"per_page": "10000"}))

        # Check if host is registered with subscription-manager (unregistered hosts lack these values and are skipped)
        if "results" in erratas:

            errata_count_cri = 0
            errata_count_imp = 0
            errata_count_mod = 0
            errata_count_low = 0
            errata_count_enh = 0
            errata_count_bug = 0

            # Check if host have any errrata at all
            if "total" in erratas and "content_facet_attributes" in host and "subscription_facet_attributes" in host:
                content_view_name = host["content_facet_attributes"]["content_view"]["name"]
                content_view_id = host["content_facet_attributes"]["content_view"]["id"]
                lifecycle_environment = host["content_facet_attributes"]["lifecycle_environment"]["name"]
                lifecycle_environment_id = host["content_facet_attributes"]["lifecycle_environment"]["id"]
                subscription_os_release= host["subscription_facet_attributes"]["release_version"]
                arch = host["architecture_name"]
                subscription_status = host["subscription_status"]
                os_release = host["operatingsystem_name"]

                content_view = get_with_json(katello_api + "/content_views/" + str(content_view_id) + "/content_view_versions?environment_id=" + str(lifecycle_environment_id), json.dumps({"per_page": "10000"}))["results"]

                cv_date = content_view[0]["created_at"]

                # Go through each errata
                for errata in erratas["results"]:

                    # If it is a security errata, check the severity
                    if errata["type"] == "security":
                        if errata["severity"] == "Critical": errata_count_cri += 1
                        if errata["severity"] == "Important": errata_count_imp += 1
                        if errata["severity"] == "Moderate": errata_count_mod += 1
                        if errata["severity"] == "Low": errata_count_low += 1

                    if errata["type"] == "enhancement": errata_count_enh += 1
                    if errata["type"] == "bugfix": errata_count_bug += 1

            # Calculate weighted score
            score = factor_cri * errata_count_cri + factor_imp * errata_count_imp + factor_mod * errata_count_mod + factor_low * errata_count_low + factor_bug * errata_count_bug + factor_enh * errata_count_enh

            # Print result
            print str(host["id"]) + "," + str(host["organization_name"]) + "," + host["name"] + "," + str(errata_count_cri) + "," + str(errata_count_imp) + "," + str(errata_count_mod) + "," + str(errata_count_low) + "," + str(errata_count_bug) + "," + str(errata_count_enh) + "," + str(score) + "," + str(content_view_name) + "," + str(cv_date) + "," + str(lifecycle_environment) + "," + str(subscription_os_release) + "," + str(os_release) + "," + str(arch) + "," + str(subscription_status) + "," + str(host["comment"])

def library_currency():

    # Print headline
    print "system_id,org_name,name,total_available_security,critical,important,moderate,low,bug,enhancement,score,total_applicable_security,applicable_critical,applicable_important,applicable_moderate,applicable_low,applicable_bug,applicable_enhancement,applicable_score,content_view,content_view_publish_date,lifecycle_environment,subscription_os_release,os_release,arch,subscription_status,comment"
    # Open reports files
    available_file = open('available_errata.csv', 'w')
    available_file.write('system_id,org_name,name,state,errata_id,issued,updated,severity,type,reboot_suggested,title,further_info\n')
    applicable_file = open('applicable_errata.csv', 'w')
    applicable_file.write('system_id,org_name,name,state,errata_id,issued,updated,severity,type,reboot_suggested,title,further_info\n')

    # Red Hat errata URL
    RH_URL = "https://access.redhat.com/errata/"
    # Fedora EPEL errata URL
    EPEL_URL = "https://bodhi.fedoraproject.org/updates"

    # Find organization
    organization = get_with_json(katello_api + "/organizations/?Search=" + args.organization, json.dumps({"per_page": "10000"}))["results"]
    organization_id = organization[0]["id"]
    # print str(organization_id)

    # Find lifecycle_environment
    lifecycle_environment_compare = get_with_json(katello_api + "/organizations/" + str(organization_id) + "/environments?name=" + args.environment , json.dumps({"per_page": "10000"}))["results"]
    lifecycle_environment_compare_id = lifecycle_environment_compare[0]["id"]
    # print str(lifecycle_environment_compare_id)

    # Find content view
    content_view_compare = get_with_json(katello_api +"/organizations/" + str(organization_id) + "/content_views?name=" + args.contentview , json.dumps({"per_page": "10000"}))["results"]
    content_view_compare_id = content_view_compare[0]["id"]
    # print str(content_view_compare_id)

    # Get all hosts (if you have more than 10000 hosts, this method will take too long itme)
    hosts = get_with_json(api + "hosts", json.dumps({"per_page": "10000"}))["results"]

    # Multiply factors according to "spacewalk-report system-currency"
    factor_cri = 32
    factor_imp = 16
    factor_mod = 8
    factor_low = 4
    factor_bug = 2
    factor_enh = 1

    for host in hosts:

        # Get all errata for each host
        erratas = get_with_json(api + "hosts/" + str(host["id"]) + "/errata", json.dumps({"per_page": "10000"}))
        applicable_erratas = get_with_json(api + "hosts/" + str(host["id"]) + "/errata?environment_id=" + str(lifecycle_environment_compare_id) + "&content_view_id=" +str(content_view_compare_id), json.dumps({"per_page": "10000"}))

        # Check if host is registered with subscription-manager (unregistered hosts lack these values and are skipped)
        if "results" in erratas:

            errata_count_sec = 0
            errata_count_cri = 0
            errata_count_imp = 0
            errata_count_mod = 0
            errata_count_low = 0
            errata_count_enh = 0
            errata_count_bug = 0

            applicable_errata_count_sec = 0
            applicable_errata_count_cri = 0
            applicable_errata_count_imp = 0
            applicable_errata_count_mod = 0
            applicable_errata_count_low = 0
            applicable_errata_count_enh = 0
            applicable_errata_count_bug = 0

            # Check if host have any errrata at all
            if "total" in erratas and "content_facet_attributes" in host and "subscription_facet_attributes" in host:
                content_view_name = host["content_facet_attributes"]["content_view"]["name"]
                content_view_id = host["content_facet_attributes"]["content_view"]["id"]
                lifecycle_environment = host["content_facet_attributes"]["lifecycle_environment"]["name"]
                lifecycle_environment_id = host["content_facet_attributes"]["lifecycle_environment"]["id"]
                subscription_os_release= host["subscription_facet_attributes"]["release_version"]
                arch = host["architecture_name"]
                subscription_status = host["subscription_status"]
                os_release = host["operatingsystem_name"]

                content_view = get_with_json(katello_api + "/content_views/" + str(content_view_id) + "/content_view_versions?environment_id=" + str(lifecycle_environment_id), json.dumps({"per_page": "10000"}))["results"]

                cv_date = content_view[0]["created_at"]

                # Go through each errata that is available
                for errata in erratas["results"]:

                    # If it is a security errata, check the severity
                    if errata["type"] == "security":
                        errata_count_sec += 1
                        if errata["severity"] == "Critical": errata_count_cri += 1
                        if errata["severity"] == "Important": errata_count_imp += 1
                        if errata["severity"] == "Moderate": errata_count_mod += 1
                        if errata["severity"] == "Low": errata_count_low += 1

                    if errata["type"] == "enhancement": errata_count_enh += 1
                    if errata["type"] == "bugfix": errata_count_bug += 1

                    # Delete any commas from the errata title
                    # eg: https://access.redhat.com/errata/RHSA-2017:0817
                    errata["title"] = errata["title"].replace(',', '')
                    available_file.write ( str(host["id"]) + "," + str(host["organization_name"]) + "," + host["name"] + ",Available," + str(errata["errata_id"]) + "," + str(errata["issued"]) + "," + str(errata["updated"]) + "," + str(errata["severity"]) + "," + str(errata["type"]) + "," + str(errata["reboot_suggested"]) + "," + str(errata["title"]) + "," + str(RH_URL) + str(errata["errata_id"]) + '\n')

                # Go through each errata that is applicable (in the library)
                for errata in applicable_erratas["results"]:

                    # If it is a security errata, check the severity
                    if errata["type"] == "security":
                        applicable_errata_count_sec +=1
                        if errata["severity"] == "Critical": applicable_errata_count_cri += 1
                        if errata["severity"] == "Important": applicable_errata_count_imp += 1
                        if errata["severity"] == "Moderate": applicable_errata_count_mod += 1
                        if errata["severity"] == "Low": applicable_errata_count_low += 1

                    if errata["type"] == "enhancement": applicable_errata_count_enh += 1
                    if errata["type"] == "bugfix": applicable_errata_count_bug += 1

                    # Delete any commas from the errata title
                    # eg: https://access.redhat.com/errata/RHSA-2017:0817
                    errata["title"] = errata["title"].replace(',', '')
                    # print str(host["id"]) + "," + host["name"] + ",Applicable," + str(errata["errata_id"]) + "," + str(errata["issued"]) + "," + str(errata["updated"]) + "," + str(errata["severity"]) + "," + str(errata["type"]) + "," + str(errata["reboot_suggested"]) + "," + str(errata["updated"]) + "," + str(errata["title"]) + ",<a href=\"https://access.redhat.com/errata/" + str(errata["errata_id"]) + "\">" + str(errata["errata_id"]) + "</a>"
                    applicable_file.write ( str(host["id"]) + "," + str(host["organization_name"]) + "," + host["name"] + ",Applicable," + str(errata["errata_id"]) + "," + str(errata["issued"]) + "," + str(errata["updated"]) + "," + str(errata["severity"]) + "," + str(errata["type"]) + "," + str(errata["reboot_suggested"]) + "," + str(errata["title"])  + "," + str(RH_URL) + str(errata["errata_id"]) + '\n')

            # Calculate weighted score
            score = factor_cri * errata_count_cri + factor_imp * errata_count_imp + factor_mod * errata_count_mod + factor_low * errata_count_low + factor_bug * errata_count_bug + factor_enh * errata_count_enh
            applicable_score = factor_cri * applicable_errata_count_cri + factor_imp * applicable_errata_count_imp + factor_mod * applicable_errata_count_mod + factor_low * applicable_errata_count_low + factor_bug * applicable_errata_count_bug + factor_enh * applicable_errata_count_enh

            # Print result
            print str(host["id"]) + "," + str(host["organization_name"]) + "," + host["name"] + "," + str(errata_count_sec) + "," + str(errata_count_cri) + "," + str(errata_count_imp) + "," + str(errata_count_mod) + "," + str(errata_count_low) + "," + str(errata_count_bug) + "," + str(errata_count_enh) + "," + str(score) + ","  + str(applicable_errata_count_sec) + "," + str(applicable_errata_count_cri) + "," + str(applicable_errata_count_imp) + "," + str(applicable_errata_count_mod) + "," + str(applicable_errata_count_low) + "," + str(applicable_errata_count_bug) + "," + str(applicable_errata_count_enh) + "," + str(applicable_score) + "," + str(content_view_name) + "," + str(cv_date) + "," + str(lifecycle_environment) + "," + str(subscription_os_release) + "," + str(os_release) + "," + str(arch) + "," + str(subscription_status) + "," + str(host["comment"])

    available_file.closed
    applicable_file.closed

if __name__ == "__main__":

    if args.advanced:
        advanced_currency()
    if args.library:
        library_currency()
    else:
        simple_currency()
