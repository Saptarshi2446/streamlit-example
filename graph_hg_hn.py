import requests
import csv

ZABBIX_API_URL = "http://3.137.153.12:8080/api_jsonrpc.php"
UNAME = "Zabbix"
PWORD = "Paramaah@@123"

# Zabbix API headers
headers = {
    "Content-Type": "application/json-rpc"
}

# Zabbix API authentication payload
auth_payload = {
    "jsonrpc": "2.0",
    "method": "user.login",
    "params": {
        "user": UNAME,
        "password": PWORD
    },
    "id": 1
}

# Authenticate and get the authentication token
response = requests.post(ZABBIX_API_URL, json=auth_payload, headers=headers)
auth_result = response.json()
auth_token = auth_result["result"]

# Function to get all graph data
def get_all_graphs():
    graph_payload = {
        "jsonrpc": "2.0",
        "method": "graph.get",
        "params": {
            "output": ["graphid", "name"],
            "selectHosts": ["hostid", "name"],
            "selectGroups": ["groupid", "name"]
        },
        "auth": auth_token,
        "id": 2
    }
    response = requests.post(ZABBIX_API_URL, json=graph_payload, headers=headers)
    graph_result = response.json()
    return graph_result["result"]

# Main function
def main():
    graphs = get_all_graphs()
    output_rows = []

    for graph in graphs:
        graph_id = graph["graphid"]
        graph_name = graph["name"]
        host = graph["hosts"][0]
        hostname = host["name"]
        host_groups = graph["groups"]
        host_group_names = [group["name"] for group in host_groups]

        output_rows.append([graph_name, graph_id, hostname, ", ".join(host_group_names)])

    # Save the output to a CSV file
    csv_file = "zabbix_graphs.csv"
    with open(csv_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Graph Name", "Graph ID", "Hostname", "Host Group Names"])
        writer.writerows(output_rows)

    print(f"CSV file '{csv_file}' has been created.")

# Run the main function
if __name__ == "__main__":
    main()
