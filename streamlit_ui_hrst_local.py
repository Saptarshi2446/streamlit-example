import json
import re
import datetime as dt
from datetime import datetime, time, timedelta
import os
import tempfile
from fpdf import FPDF
import streamlit as st
import subprocess
import base64
from PIL import Image
from pytz import timezone
import pandas as pd
import matplotlib.pyplot as plt
from streamlit_option_menu import option_menu
import seaborn as sns
from streamlit_extras.app_logo import add_logo
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from matplotlib.backends.backend_pdf import PdfPages
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PyPDF2 import PageObject
import streamlit_authenticator as stauth
import csv
import requests
import numpy as np
import ast
from psycopg2 import sql
from yaml.loader import SafeLoader
import yaml
import hydralit_components as hc
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import psycopg2
import io

st.set_page_config(layout='wide',initial_sidebar_state='collapsed',)

with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

authenticator.login('Login', 'main')


if st.session_state["authentication_status"]:
    menu_data = [
            # Adding blank space
        {'label': "   "},
        {'label': "   "},
        {'icon': "far fa-copy", 'label': "Infrastructure Details"},
            # Adding blank space
        {'label': "   "},
            # Adding blank space
        {'label': "   "},    # Adding blank space
        {'icon': "fa-solid fa-radar", 'label': "Host", 'submenu': [
            {'id': 'subid11', 'icon': "fa fa-paperclip", 'label': "Host Details"},
            {'id': 'subid12', 'icon': "💀", 'label': "Add Hosts"},
            {'id': 'subid13', 'icon': "fa fa-database", 'label': "Hosts"}
        ]},
            # Adding blank space
        {'label': "   "},
        # Adding blank space
        {'label': "   "},
        {'icon': "far fa-chart-bar", 'label': "Uptimes"},
            # Adding blank space
        {'label': "   "},
        # Adding blank space
        {'label': "   "},
        {'label': "Reports"},
            # Adding blank space
        {'label': "   "},
        # Adding blank space
        {'label': "   "},
        {'icon': "fas fa-tachometer-alt", 'label': "Graph", 'ttip': "I'm the Dashboard tooltip!"},
            # Adding blank space
        {'label': "   "},    # Adding blank space
        {'label': "   "},
        {'icon': "far fa-copy", 'label':"SLA"},
            # Adding blank space
        {'label': "   "},    # Adding blank space
        {'label': "   "},
        {'icon': "fa-solid fa-radar",'label':"UI Server"},
            # Adding blank space
        {'label': "   "},    # Adding blank space
        {'label': "   "},
        {'icon': "fa-solid fa-radar",'label':"User", 'submenu':[{'label':"Info", 'icon': "fa fa-meh"},{'label':"Config"}]},
        {'label': "   "},    # Adding blank space
        {'label': "   "},
    ]

    over_theme = {'txc_inactive': '#000000'}
    menu_id = hc.nav_bar(
        menu_definition=menu_data,
        override_theme=over_theme,
        home_name='Home',
        login_name='Logout',
        hide_streamlit_markers=True, #will show the st hamburger as well as the navbar now!
        sticky_nav=True, #at the top or not
        sticky_mode='pinned', #jumpy or not-jumpy, but sticky or pinned
    )
    if menu_id == "Reports":
        # Function to get item details by item ID
        def get_item_details(item_id, auth_token):
            item_payload = {
                "jsonrpc": "2.0",
                "method": "item.get",
                "params": {
                    "itemids": [int(item_id)],  # Convert to int
                    "output": ["name", "value_type"]
                },
                "auth": auth_token,
                "id": 2
            }
            response = requests.post(ZABBIX_API_URL, data=json.dumps(item_payload), headers=headers, verify=False)
            item_result = response.json()
            return item_result["result"][0]

        # Function to get the last 10 history values for an item
        def get_history_values(item_id, value_type, time_from, time_to, auth_token):
            history_payload = {
                "jsonrpc": "2.0",
                "method": "history.get",
                "params": {
                    "output": "extend",
                    "history": value_type,
                    "itemids": int(item_id),  # Convert to int
                    "sortfield": "clock",
                    "sortorder": "ASC",
                    "time_from": int(time_from),  # Convert to int
                    "time_till": int(time_to)  # Convert to int
                },
                "auth": auth_token,
                "id": 3
            }
            response = requests.post(ZABBIX_API_URL, data=json.dumps(history_payload), headers=headers, verify=False)
            history_result = response.json()
            return history_result["result"]

        def format_value(item_name, value):
            if "interface" in item_name.lower() and "bits" in item_name.lower():
                # Formatting for network values (same as before)
                try:
                    value = float(value)
                    if value >= 1000000000:
                        return f"{value / 1000000000:.2f} Gbps"
                    elif value >= 1000000:
                        return f"{value / 1000000:.2f} Mbps"
                    elif value >= 1000:
                        return f"{value / 1000:.2f} Kbps"
                    else:
                        return f"{value:.2f} bps"
                except ValueError:
                    return value
            elif "space" in item_name.lower() or "memory" in item_name.lower():
                # Formatting for storage values
                try:
                    value = float(value)
                    if value >= 1024 ** 3:
                        return f"{value / 1024 ** 3:.2f} GB"
                    elif value >= 1024 ** 2:
                        return f"{value / 1024 ** 2:.2f} MB"
                    elif value >= 1024:
                        return f"{value / 1024:.2f} KB"
                    else:
                        return f"{value:.2f} bytes"
                except ValueError:
                    return value
            else:
                return value
        def convert_graph_to_pdf_reports(fig):
            fig.set_size_inches(8.375, 4)  
            pdf_bytes = io.BytesIO()
            with PdfPages(pdf_bytes) as pdf:
                pdf.savefig(fig, bbox_inches='tight')
            pdf_bytes.seek(0)
            filename=f"line_graph.pdf"
            script_directory ="."
            script_pdf_path = os.path.join(script_directory, filename)
            with PdfPages(script_pdf_path) as pdf:
                pdf.savefig(fig, bbox_inches='tight')
            return pdf_bytes.getvalue()
        # Load the CSV data
        def save_figure_as_jpeg(fig, filename):
            fig.savefig(filename, format='jpeg', bbox_inches='tight')

        def save_figure_as_png(fig, filename):
            fig.savefig(filename, format='png', bbox_inches='tight')

        def save_figure_as_svg(fig, filename):
            fig.savefig(filename, format='svg', bbox_inches='tight')

        def save_data_to_csv(df):
            csv_file_csv = "data.csv"
            df.to_csv(csv_file_csv, index=False)
            return csv_file_csv

        def save_data_to_pdf(df):
            pdf_file = "data.pdf"

            # Convert DataFrame to a list of lists for tabular data
            table_data = [df.columns.tolist()] + df.values.tolist()
            
            # Create a PDF document using reportlab
            doc = SimpleDocTemplate(pdf_file, pagesize=landscape(letter))
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
                ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 0), (-1, -1), (0.9, 0.9, 0.9)),
                ('GRID', (0, 0), (-1, -1), 1, (0.5, 0.5, 0.5)),
            ]))
            
            doc.build([table])
            return pdf_file
        def get_history_local(item_id,start_timestamp,end_timestamp,auth_token):
            time_from = start_timestamp
            time_to = end_timestamp
            item_details = get_item_details(item_id,auth_token)
            # Get the item name and replace non-alphanumeric characters with underscores
            item_name = re.sub(r'[^a-zA-Z0-9]', '_', item_details["name"])
            value_type = item_details["value_type"]

            history_values = get_history_values(item_id, value_type, time_from, time_to,auth_token)
            output_rows = []

            for entry in history_values:
                unix_timestamp = int(entry["clock"])
                human_readable_time = datetime.fromtimestamp(unix_timestamp).strftime("%Y-%m-%d %H:%M:%S")
                value = entry["value"]
                output_rows.append([human_readable_time, item_name, value])

            # Create a temporary CSV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
                csv_file = f"{item_name}.csv"

                with open(csv_file, mode="w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Time", "Item Name", "Value"])
                    writer.writerows(output_rows)

            # Load the CSV file
            df = pd.read_csv(csv_file)

            # Apply formatting conditionally
            df['Value'] = df.apply(lambda row: format_value(row['Item Name'], row['Value']), axis=1)

            # Save the modified DataFrame back to the same temporary CSV file
            df.to_csv(csv_file, index=False)

        data = pd.read_csv('file.csv')

        # Get unique hostgroup names
        hostgroups = data['hostgroup'].unique()

        # Columns layout
        col1, col2 = st.columns([2, 4])
        with col1: 
            # Hostgroup selectbox
            selected_hostgroup = st.selectbox('Select Hostgroup', [' - '] + list(hostgroups),key="hrg2")

            # Filter data based on selected hostgroup
            filtered_data = data[data['hostgroup'] == selected_hostgroup] if selected_hostgroup != ' - ' else data

            # Get unique hostnames within the selected hostgroup
            hostnames = filtered_data['hostname'].unique()

            # Hostname selectbox
            selected_hostname = st.selectbox('Select Hostname', [' - '] + list(hostnames),key="hstn2")

            # Filter data based on selected hostname
            final_data = filtered_data[filtered_data['hostname'] == selected_hostname] if selected_hostname != ' - ' else filtered_data

            # Get unique item names for the selected hostname
            item_names = final_data['itemname'].unique()

            # Itemname selectbox
            selected_itemname = st.selectbox('Select Itemname', [' - '] + list(item_names),key="itn1")

            col3 , col4 = st.columns(2)
            selected_date = col3.date_input("Select Start Date", key="Date1")

                #col6, col7, col8 = st.columns(3)
            selected_time = col4.selectbox("Select Start Time", [dt.time(0, 0, 0)] + [dt.time(s // 3600, (s // 60) % 60, s % 60) for s in range(0, 24 * 60 * 60, 1)], format_func=lambda t: t.strftime("%H:%M:%S"))
            time_value1 = datetime.combine(selected_date, selected_time)
            col5, col6 = st.columns(2)
            selected_date2 = col5.date_input("Select End Date", key="Date2")

            # col9, col10, col11 = st.columns(3)
            selected_time2 = col6.selectbox("Select End Time", [dt.time(0, 0, 0)] + [dt.time(s // 3600, (s // 60) % 60, s % 60) for s in range(0, 24 * 60 * 60, 1)], format_func=lambda t: t.strftime("%H:%M:%S"))
            time_value2 = datetime.combine(selected_date2, selected_time2)
            start_timestamp = int(time_value1.timestamp())
            end_timestamp = int(time_value2.timestamp())
            print(start_timestamp)
            print(end_timestamp)



            
        File_availability = False
        load = col1.button('Execute')
        if "load_state" not in st.session_state:
            st.session_state.load_state = False
        if load or st.session_state.load_state:
            st.session_state.load_state = True
            if selected_itemname != ' - ':
                ZABBIX_API_URL = "http://18.222.141.167:8080/api_jsonrpc.php"
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
                response = requests.post(ZABBIX_API_URL, data=json.dumps(auth_payload), headers=headers, verify=False)
                auth_result = response.json()
                auth_token = auth_result["result"]
                        # Display selected data
                print('Selected Hostgroup:', selected_hostgroup)
                print('Selected Hostname:', selected_hostname)
                print('Selected Itemname:', selected_itemname)
                selected_itemname_refined = re.sub(r'[^a-zA-Z0-9]', '_', selected_itemname)
                # Optionally, you can display the details of the selected itemname
                selected_item_data = final_data[final_data['itemname'] == selected_itemname]
                if not selected_item_data.empty:
                    item_id = selected_item_data.iloc[0]['itemid']
                    with col2:
                        st.write(" ")
                        st.write(" ")
                        st.dataframe(selected_item_data, width=2000)
                        get_history_local(item_id,start_timestamp,end_timestamp,auth_token)
        #                subprocess.run(["python", "ishan_item_history_local.py", str(item_id),str(start_timestamp),str(end_timestamp)])
                        csv_file_org = f"{selected_itemname_refined}.csv"
                        df = pd.read_csv(csv_file_org)
                        st.dataframe(df,width = 2000,height= 300)
                        File_availability = True
                        
                        saved_csv_file = save_data_to_csv(df)

                        saved_pdf_file = save_data_to_pdf(df)

                        # Read the saved CSV and PDF files as bytes
                        with open(saved_csv_file, "rb") as csv_file:
                            csv_bytes = csv_file.read()

                        with open(saved_pdf_file, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()

                        # Convert bytes to base64 for embedding in HTML
                        b64_csv = base64.b64encode(csv_bytes).decode()
                        b64_pdf = base64.b64encode(pdf_bytes).decode()

                        # Generate download links for CSV and PDF
                        href_csv = f"""
                            <a style="
                                text-decoration: none;
                                display: inline-block;
                                padding: 8px 8px;
                                background-color: #f5f5f5;
                                color: black;
                                border-radius: 4px;
                                border: black;
                            "
                            href="data:text/csv;base64,{b64_csv}" download="data.csv">
                                Download CSV
                            </a>
                        """

                        href_pdf = f"""
                            <a style="
                                text-decoration: none;
                                display: inline-block;
                                padding: 8px 8px;
                                background-color: #f5f5f5;
                                color: black;
                                border-radius: 4px;
                                border: black;
                            "
                            href="data:application/pdf;base64,{b64_pdf}" download="data.pdf">
                                Download PDF
                            </a>
                        """
                        col12,col13=st.columns(2)

                        # Render the download links
                        col12.markdown(href_csv, unsafe_allow_html=True)
                        col13.markdown(href_pdf, unsafe_allow_html=True)

                        # col3,col4 = st.columns(2)
                        # csv_buffer = BytesIO()
                        # df.to_csv(csv_buffer, index=False)
                        # csv_buffer.seek(0)
                        # b64 = base64.b64encode(csv_buffer.read()).decode()
                        # col3.download_button("Download CSV File", data=csv_buffer, file_name="data.csv", key="csv")

                        # pdf_buffer = BytesIO()
                        # pdf = df.to_markdown()
                        # pdf_buffer.write(pdf.encode('utf-8'))
                        # pdf_buffer.seek(0)
                        # b64 = base64.b64encode(pdf_buffer.read()).decode()
                        # col4.download_button("Download PDF File", data=pdf_buffer, file_name="data.pdf")

        st.markdown('<hr style="margin-left: 0.5cm; margin-right: 0.5cm; border-top: 3px double black; margin-top: 0.5rem; margin-bottom: 0.5rem;">', unsafe_allow_html=True)
        col3 , col4 = st.columns([4,2.5])

        if File_availability == True :
            

            import pandas as pd
            import matplotlib.pyplot as plt
            import streamlit as st
            from matplotlib.ticker import MaxNLocator, FixedLocator
            import numpy as np
            import re

            # Read CSV data
            data = pd.read_csv(csv_file_org)

            # Extract column data
            x_values = data["Time"]
            y_label = data.columns[2]  # Get the second column name
            y_values = data[y_label]
            y_values_with_units = data[y_label]

            # Extract numeric values from y_values_with_units using regular expressions
            numeric_values = y_values_with_units.apply(lambda value: float(re.search(r'[\d.]+', value).group()))

            # Custom CSS style for the title
            title_style = "font-size: 28px; font-weight: bold; text-decoration: underline"
            custom_title = f'<h1 style="{title_style}">Bar Graph</h1>'
            col3.markdown(custom_title, unsafe_allow_html=True)

            # Create a Matplotlib figure (fig)
            fig, ax = plt.subplots(figsize=(10, 6))

            # Plot the bar graph
            ax.bar(x_values, numeric_values)  # Use extracted numeric values

            # Set x-axis label
            ax.set_xlabel("Time", fontsize=8)

            # Set y-axis label
            ax.set_ylabel(y_label, fontsize=8)

            # Set the title
            ax.set_title(f"{y_label} vs Time", fontsize=8)

            # Use MaxNLocator for intelligently setting y-axis tick locations
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            # Determine the step size for x-axis tick labels based on the total number of values
            total_x_values = len(x_values)
            desired_num_ticks = 30
            step_size = max(1, total_x_values // desired_num_ticks)

            # Manually set x-axis tick labels
            x_tick_locations = np.arange(0, total_x_values, step_size)
            x_tick_labels = [x_values[i] for i in x_tick_locations]
            ax.set_xticks(x_tick_locations)
            ax.set_xticklabels(x_tick_labels, rotation=90, fontsize=6)  # Rotate x-axis labels by 45 degrees

            # y_max = max(numeric_values)
            # y_min = min(numeric_values)
            # y_range = y_max - y_min

            # if y_range > 10:
            #     y_step = int(y_range / 20)
            # else:
            #     y_step = 1

            # y_ticks = np.arange(0, y_max + y_step, y_step)
            # ax.yaxis.set_major_locator(FixedLocator(y_ticks))
            #     total_y_values = len(y_values)
            # desired_num_ticks = 30
            # step_size = max(1, total_y_values // desired_num_ticks)

            # y_tick_locations = np.arange(0, total_y_values, step_size)
            # y_tick_labels = [y_values[i] for i in y_tick_locations]
            # ax.set_yticks(y_tick_locations)
            # ax.set_yticklabels(y_tick_labels, rotation=0, fontsize=6)

            # Display the Matplotlib figure using Streamlit
            col3.pyplot(fig)

            # Assuming y_values is a pandas Series containing the values with units
            first_row_value = x_values.iloc[1]
            last_row_value = x_values.iloc[-1]
            Start = f"{first_row_value} "
            End =  f"{last_row_value}"
            # Extract numeric values using regular expressions
            numeric_values = y_values.apply(lambda value: float(re.search(r'[\d.]+', value).group()))

            # Calculate summary statistics
            max_value = numeric_values.max()
            min_value = numeric_values.min()
            avg_value = numeric_values.mean()
            sum_value = numeric_values.sum()

            # Create summary DataFrames
            summary_data = pd.DataFrame({
                "Start Period": [Start],
                "End Period": [End],
                "Max Value": [max_value],
                "Min Value": [min_value],
                "Average Value": [avg_value],
                "Sum of Values": [sum_value]
            })

            summary_data_no_sum = pd.DataFrame({
                "Start Period": [Start],
                "End Period": [End],
                "Max Value": [max_value],
                "Min Value": [min_value],
                "Average Value": [avg_value]
            })

            # Save the figure as a larger JPEG image
            larger_graph_image_path = "larger_line_graph_3.svg"
            plt.savefig(larger_graph_image_path, format="svg", dpi=300, bbox_inches="tight")

            # Display summary data table
            dataframe_title = f'<h1 style="{title_style}">Value Data</h1>'
            col4.markdown(dataframe_title, unsafe_allow_html=True)
            # Transpose the summary data DataFrame to display vertically
            col4.write("")
            col4.write("")
            summary_data_vertical = summary_data.T
            summary_data_no_sum_vertical = summary_data_no_sum.T
            

            pdf_content_bar = convert_graph_to_pdf_reports(fig)

            pdf_filename_bar = f"line_graph.pdf"
            b64_pdf = base64.b64encode(pdf_content_bar).decode()
            # HTML code for the download button
            href_pdf = f"""
        <a style="
            text-decoration: none;
            display: inline-block;
            padding: 8px 8px;
            background-color: #f5f5f5;
            color: black;
            border-radius: 4px;
            border: black;
        "
        href="data:application/pdf;base64,{b64_pdf}" download="bar_chart.pdf">
            Download PDF
        </a>
            """

            # CSS styles
            css_styles = """
            <style>
            .download-container {
                border: 1px solid #ccc;
                padding: 5px;
                display: inline-block;
                background-color: #f5f5f5;
            }

            .button {
                text-decoration: none;
                display: inline-block;
                padding: 5px 5px;
                background-color: #f5f5f5;
                color: white;
                border: black;
                border-radius: 4px;
            }
            </style>
            """
            jpeg_filename_bar = "bar_chart.jpeg"
            png_filename_bar = "bar_chart.png"
            svg_filename_bar = "bar_chart.svg"

            # Convert figures to respective formats
            save_figure_as_jpeg(fig, jpeg_filename_bar)
            save_figure_as_png(fig, png_filename_bar)
            save_figure_as_svg(fig, svg_filename_bar)
            
            jpeg_href = f"""
        <a style="
            text-decoration: none;
            display: inline-block;
            padding: 8px 8px;
            background-color: #f5f5f5;
            color: black;
            border-radius: 4px;
            border: black;
        "
        href="data:image/jpeg;base64,{base64.b64encode(open(jpeg_filename_bar, 'rb').read()).decode()}" download="bar_chart.jpeg">
            Download JPEG
        </a>
        """

            png_href = f"""
        <a style="
            text-decoration: none;
            display: inline-block;
            padding: 8px 8px;
            background-color: #f5f5f5;
            color: black;
            border-radius: 4px;
            border: black;
        "
        href="data:image/png;base64,{base64.b64encode(open(png_filename_bar, 'rb').read()).decode()}" download="bar_chart.png">
            Download PNG
        </a>
        """

            svg_href = f"""
        <a style="
            text-decoration: none;
            display: inline-block;
            padding: 8px 8px;
            background-color: #f5f5f5;
            color: black;
            border-radius: 4px;
            border: black;
        "
        href="data:image/svg+xml;base64,{base64.b64encode(open(svg_filename_bar, 'rb').read()).decode()}" download="bar_chart.svg">
            Download SVG
        </a>
        """
            
            with col4:
                on = st.toggle('Get Sum')

                if on:
                    st.write('Sum added')

                    st.dataframe(summary_data_vertical,width=1200,height=250)
                else:
                    st.dataframe(summary_data_no_sum_vertical,width=1200,height=250)
                st.markdown(dataframe_title, unsafe_allow_html=True)
                st.write(" ")
                col15,col16,col17,col18 = st.columns(4)
                col18.markdown(png_href, unsafe_allow_html=True)
                col17.markdown(jpeg_href, unsafe_allow_html=True)
                col16.markdown(svg_href, unsafe_allow_html=True)
                st.markdown(css_styles, unsafe_allow_html=True)
                col15.markdown(f"{href_pdf}", unsafe_allow_html=True)
    
    if menu_id == "Infrastructure Details":
        import folium
        from streamlit_folium import folium_static
        import streamlit as st
        import pandas as pd
        # Load the CSV file into a DataFrame
        @st.cache_data
        def load_data():
            data = pd.read_csv('inventory.csv')
            return data

        df = load_data()

        # Create a Streamlit UI
        st.title("CSV File Viewer with Filters and Map Plots")
        col1i, col2i, col3i, col4i, col5i, col6i = st.columns(6)

        # Create filters for specific columns
        os_filter = col1i.multiselect("Filter OS", df['os'].unique())
        hardware_filter = col2i.multiselect("Filter Hardware", df['hardware'].unique())
        location_filter = col3i.multiselect("Filter Location", df['location'].unique())
        model_filter = col4i.multiselect("Filter Model", df['model'].unique())
        vendor_filter = col5i.multiselect("Filter Vendor", df['vendor'].unique())
        type_filter = col6i.multiselect("Filter Type", df['type'].unique())

        col7i, col8i = st.columns([3.5, 3])

        with col7i:
            # Apply filters to the DataFrame
            filtered_df = df.copy()

            if os_filter:
                filtered_df = filtered_df[filtered_df['os'].isin(os_filter)]
            if hardware_filter:
                filtered_df = filtered_df[filtered_df['hardware'].isin(hardware_filter)]
            if location_filter:
                filtered_df = filtered_df[filtered_df['location'].isin(location_filter)]
            if model_filter:
                filtered_df = filtered_df[filtered_df['model'].isin(model_filter)]
            if vendor_filter:
                filtered_df = filtered_df[filtered_df['vendor'].isin(vendor_filter)]
            if type_filter:
                filtered_df = filtered_df[filtered_df['type'].isin(type_filter)]

            # Display the filtered DataFrame
            st.write("Filtered DataFrame:")
            st.dataframe(filtered_df,height = 465)

        with col8i:

            col9i,col10i=st.columns([0.5,4])
            with col9i:
                st.write("")
            with col10i:
                # with st.expander("Map Plot"):
                if not filtered_df.empty:
                    # Create a Folium map based on the filtered DataFrame
                    m = folium.Map(location=[filtered_df['latitude'].mean(), filtered_df['longitude'].mean()],zoom_start=1.5, tiles='OpenStreetMap',width=750)

                    for index, row in filtered_df.iterrows():
                        popup_content = f"Name: {row['name']}<br>Location: {row['location']}"
                        folium.Marker([row['latitude'], row['longitude']], popup=folium.Popup(popup_content, max_width=300)).add_to(m)

                        # folium.Marker([row['latitude'], row['longitude']], popup=row['name','location']).add_to(m)

                    # Display the map using folium_static
                    folium_static(m)
                else:
                    st.warning("No data to display on the map. Please apply filters.")
    if menu_id == "SLA":
        url = "http://18.222.141.167:8080/api_jsonrpc.php"
        user = "Zabbix"
        password = "Paramaah@@123"
        auth_data = {
            'jsonrpc': '2.0',
            'method': 'user.login',
            'params': {
                'user': user,
                'password': password,
            },
            'id': 1,
        }
        response = requests.post(url, json=auth_data, verify=False)
        auth_token = json.loads(response.content)['result']

        r = requests.post(url,
                        json={
                            "jsonrpc": "2.0",
                            'method': 'sla.get',
                            'params': {
                                    "output": "extend",
                                    "selectServiceTags": ["tag", "value"]
                            },
                            "id": 2,
                            "auth": auth_token
                        })



        json_object = json.dumps(r.json(), indent=4, sort_keys=True)

        print(json_object)
        with open("sla_list.json", "w") as outfile:
            outfile.write(json_object)

        with open('sla_list.json') as json_file:
            data = json.load(json_file)

        result_data = data['result']

        # now we will open a file for writing
        data_file = open('sla_list.csv', 'w')


        # create the csv writer object
        csv_writer = csv.writer(data_file)


        count = 0
        for name in result_data:
            if count == 0:
        
                # Writing headers of CSV file
                header = name.keys()
                csv_writer.writerow(header)
                count += 1
        
            # Writing data of CSV file
            csv_writer.writerow(name.values())

        data_file.close()

        import pandas as pd

        # Load the CSV file into a DataFrame
        df = pd.read_csv('sla_list.csv')

        # Remove leading/trailing whitespace from column names
        df.columns = df.columns.str.strip()

        # Write the cleaned DataFrame to a new CSV file
        df.to_csv('cleaned_sla_file.csv', index=False)



        r = requests.post(url,
                        json={
                            "jsonrpc": "2.0",
                            'method': 'service.get',
                            'params': {
                                    "output": "extend",
                                    "selectTags": "extend"
                            },
                            "id": 2,
                            "auth": auth_token
                        })

        print(json.dumps(r.json(), indent=4, sort_keys=True))

        json_object = json.dumps(r.json(), indent=4, sort_keys=True)

        print(json_object)
        with open("service_list.json", "w") as outfile:
            outfile.write(json_object)

        with open('service_list.json') as json_file:
            data = json.load(json_file)

        result_data = data['result']

        # now we will open a file for writing
        data_file = open('service_list.csv', 'w')


        # create the csv writer object
        csv_writer = csv.writer(data_file)


        count = 0
        for name in result_data:
            if count == 0:
        
                # Writing headers of CSV file
                header = name.keys()
                csv_writer.writerow(header)
                count += 1
        
            # Writing data of CSV file
            csv_writer.writerow(name.values())

        data_file.close()

        import pandas as pd

        # Load the CSV file into a DataFrame
        df = pd.read_csv('service_list.csv')

        # Remove leading/trailing whitespace from column names
        df.columns = df.columns.str.strip()

        # Write the cleaned DataFrame to a new CSV file
        df.to_csv('cleaned_service_file.csv', index=False)



        #Logout user
        print("\nLogout user")
        r = requests.post(url,
                        json={
                            "jsonrpc": "2.0",
                            "method": "user.logout",
                            "params": {},
                            "id": 2,
                            "auth": auth_token
                        })

        print(json.dumps(r.json(), indent=4, sort_keys=True))
        conn = psycopg2.connect(database="zabbix_db1", user="zabbixuser", password="zabbixpass", host="18.222.141.167", port="5432")
        def execute_query(SLA_Name,Service_Name):
            # Define the headers for the CSV file
            headers = ['serviceid']

            # Define the SQL query
            query = sql.SQL("""
            SELECT 
                serviceid 
            FROM 
                services
            WHERE 
                name = %s;
            """)

            # Execute the query and retrieve the data
            cursor = conn.cursor()
            cursor.execute(query,(Service_Name,))
            data = cursor.fetchall()

            # Print the query output
            print("Query output:")
            for row in data:
                print(row[0])

            # Save the query output to a CSV file
            filename = 'serviceid.csv'
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                for row in data:
                    writer.writerow(row)


            ###################   SLA ID ######################
            headers2 = ['slaid','slo','name']

            # Define the SQL query
            query2 = sql.SQL("""
            SELECT 
                slaid,slo,name
            FROM 
                sla
            WHERE 
                name = %s;
            """)

            # Execute the query and retrieve the data
            cursor = conn.cursor()
            cursor.execute(query2,(SLA_Name,))
            data2 = cursor.fetchall()

            # Print the query output
            print("Query output:")
            for row in data2:
                print(row[0])

            # Save the query output to a CSV file
            filename = 'slaid.csv'
            with open(filename, mode='w', newline='') as file2:
                writer = csv.writer(file2)
                writer.writerow(headers2)
                for row in data2:
                    writer.writerow(row)

            # Close the cursor and connection objects
            cursor.close()
            conn.close()


            # Zabbix API credentials


            # Zabbix API authentication
            auth_data = {
                'jsonrpc': '2.0',
                'method': 'user.login',
                'params': {
                    'user': user,
                    'password': password,
                },
                'id': 1,
            }
            response = requests.post(url, json=auth_data, verify=False)
            auth_token = json.loads(response.content)['result']

            # Read SLA ID from CSV file
            with open('slaid.csv') as f:
                print(f)
                reader = csv.reader(f)
                for row in reader:
                    slaid = row[0]

            # Read service ID from CSV file
            with open('serviceid.csv', 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    serviceid = row[0]

            # SLA report request
            sla_data = {
                'jsonrpc': '2.0',
                'method': 'sla.getsli',
                'params': {
                    'slaid': slaid,
                    'serviceids':serviceid,
                    'periods': 10
                },
                'auth': auth_token,
                'id': 2,
            }
            response = requests.post(url, json=sla_data, verify=False)

            sla_report = json.loads(response.content)['result']
            #print(json.dumps(sla_report, indent=4)) 
            json_object = json.dumps(sla_report, indent=4, sort_keys=True)
            with open("sla_arg_2.json", "w") as outfile:
                outfile.write(json_object)
            with open('sla_arg_2.json') as f:
                data = json.load(f)

            # find the length of the longest section
            max_len = max(len(data['periods']), len(data['serviceids']), len(data['sli']))

            # create a new list of dictionaries with missing values filled in
            rows = []
            for i in range(max_len):
                row = {}
                if i < len(data['periods']):
                    
                    period_from = datetime.fromtimestamp(data['periods'][i]['period_from']).strftime('%Y-%m-%d %H:%M:%S')
                    period_to = datetime.fromtimestamp(data['periods'][i]['period_to']).strftime('%Y-%m-%d %H:%M:%S')
                    row['period_from'] = period_from
                    row['period_to'] = period_to
                    row['days'] = (datetime.strptime(period_to, '%Y-%m-%d %H:%M:%S') - datetime.strptime(period_from, '%Y-%m-%d %H:%M:%S')).days
                else:
                    row['period_from'] = None
                    row['period_to'] = None
                    row['days'] = None
                if i < len(data['serviceids']):
                    row['service_id'] = data['serviceids'][i]
                else:
                    row['service_id'] = None
                
                if i < len(data['sli']):
                    downtime = timedelta(seconds=data['sli'][i][0]['downtime'])
                    uptime = timedelta(seconds=data['sli'][i][0]['uptime'])
                    error_budget = timedelta(seconds=data['sli'][i][0]['error_budget'])
                    excluded_downtimes = data['sli'][i][0]['excluded_downtimes']
                    sli = data['sli'][i][0]['sli']
                    row['downtime'] = str(downtime)
                    row['error_budget'] = str(error_budget)
                    row['excluded_downtimes'] = excluded_downtimes
                    row['sli'] = sli
                    row['uptime'] = str(uptime)
                else:
                    row['downtime'] = None
                    row['error_budget'] = None
                    row['excluded_downtimes'] = None
                    row['sli'] = None
                    row['uptime'] = None
                
                rows.append(row)

            # write the data to a CSV file
                File="slaName__.csv"
                with open(File, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['period_from', 'period_to', 'days','service_id', 'downtime', 'error_budget', 'excluded_downtimes', 'sli', 'uptime'])
                    writer.writeheader()
                    writer.writerows(rows)

        # Load cleaned_sla_file.csv into DataFrame
        sla_data = pd.read_csv('cleaned_sla_file.csv')

        # Function to extract the tag value based on the specified format
        def extract_tag_value(tags):
            try:
                tags_list = ast.literal_eval(tags)
                if isinstance(tags_list, list) and len(tags_list) > 0:
                    tag_info = tags_list[0]
                    tag_value = tag_info.get('tag', '').split(':')[1].strip()
                    return tag_value
            except:
                pass
            return ''

        # Apply the function to create the new "tag" column
        sla_data['tag'] = sla_data['service_tags'].apply(lambda x: x[x.find("'tag': '")+8:x.find("', 'value'")])

        # Drop the original "service_tags" column
        sla_data.drop(columns=['service_tags'], inplace=True)

        # Save the modified DataFrame as a new CSV file
        sla_data.to_csv('cleaned_sla_file_with_tag.csv', index=False)
        sla_name = sla_data["name"].unique().tolist()

        service_data = pd.read_csv('cleaned_service_file.csv')

        # Function to extract the tag value based on the specified format
        def extract_tag_value(tags):
            try:
                tags_list = ast.literal_eval(tags)
                if isinstance(tags_list, list) and len(tags_list) > 0:
                    tag_info = tags_list[0]
                    tag_value = tag_info.get('tag', '').split(':')[1].strip()
                    return tag_value
            except:
                pass
            return ''

        # Apply the function to create the new "tag" column
        service_data['tag'] = service_data['tags'].apply(lambda x: x[x.find("'tag': '")+8:x.find("', 'value'")])

        # Drop the original "tags" column
        service_data.drop(columns=['tags'], inplace=True)

        # Save the modified DataFrame as a new CSV file
        service_data.to_csv('cleaned_service_file_with_tag.csv', index=False)
        # Load the cleaned_sla_file.csv into a DataFrame
        sla_data = pd.read_csv('cleaned_sla_file_with_tag.csv')

        # Extract unique tags from the 'tag' column in SLA DataFrame
        sla_tags = sla_data['tag'].unique().tolist()
        col1, col2 = st.columns([2, 4])

        # Streamlit UI
        selected_sla_tag = col1.selectbox("Select SLA Tag", ['Select a Tag'] + sla_tags)

        if selected_sla_tag != 'Select a Tag':
            # Filter SLA data based on selected tag
            filtered_sla_data = sla_data[sla_data['tag'] == selected_sla_tag]

            # Display filtered SLA names in dropdown
            sla_name = filtered_sla_data["name"].unique().tolist()

            # Filter Service data based on selected tag
            filtered_service_data = service_data[service_data['tag'] == selected_sla_tag]

            # Display filtered Service names in dropdown
            service_name = filtered_service_data["name"].unique().tolist()
        else:
            sla_name = ['Select a Tag first']
            service_name = ['Select a Tag first']

        # Selectboxes for SLA and Service names
        SLA_Name = col1.selectbox("SLA Name", sla_name, key='sla_name_selectbox')
        Service_Name = col1.selectbox("Service Name", service_name, key='service_name_selectbox')

        # Execute button
        execute_button = col1.button("Execute Query")
        query_executed = False
        if execute_button:
            if selected_sla_tag == 'Select a Tag':
                st.warning("Please select a tag first.")
            elif SLA_Name == 'Select a Tag first':
                st.warning("Please select a tag first.")
            else:
                df = execute_query(SLA_Name, Service_Name)
                query_executed = True

        # Check if the query was executed successfully
        if query_executed:
            # Load the generated CSV file into a DataFrame
            data = pd.read_csv("slaName__.csv", low_memory=False)

            # Load the "slaid.csv" file into a separate DataFrame
            slaid_data = pd.read_csv("slaid.csv", low_memory=False)

            # Add the 'slo' and 'name' columns from slaid_data to data based on the row index
            data['slo'] = slaid_data['slo']
            data['name'] = slaid_data['name']

            # Display the data as a table on the UI
            col2.dataframe(data)

            # Add a download button to allow users to download the updated CSV file
            col2.download_button(
                label="Download Updated CSV",
                data=data.to_csv(index=False),
                file_name="updated_sla_data.csv",
                mime="text/csv",
            )
    if menu_id == "subid12":
        selected = option_menu(None, ["Single Upload", "Multiple Upload"], 
        menu_icon="cast", default_index=0, orientation="horizontal",
        styles = {
        "container": {"padding": "0!important", "background-color": "#dcdcdc"},
        "icon": {"color": "black", "font-size": "10px"},
        "nav-link": {"font-size": "15px", "text-align": "center", "margin": "0px", "--hover-color": "lightgrey"},
        "nav-link-selected": {"background-color": "grey"},
        }
    )
        # Zabbix API credentials
        ZABBIX_API_URL = "http://18.222.141.167:8080/api_jsonrpc.php"
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
            "id": 1,
            "auth": None
        }

        # Authenticate and get auth token
        response = requests.post(ZABBIX_API_URL, json=auth_payload, headers=headers)
        auth_token = response.json()["result"]
        if selected == "Single Upload":
            # Fetch hostgroups and save to CSV
                hostgroup_payload = {
                    "jsonrpc": "2.0",
                    "method": "hostgroup.get",
                    "params": {
                        "output": ["groupid", "name"],
                    },
                    "auth": auth_token,
                    "id": 2
                }

                response = requests.post(ZABBIX_API_URL, json=hostgroup_payload, headers=headers)
                hostgroups = response.json()["result"]
                with open("hostgroups.csv", "w", newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow(["Group ID", "Name"])
                    for group in hostgroups:
                        csvwriter.writerow([group["groupid"], group["name"]])

                # Fetch templates and save to CSV
                template_payload = {
                    "jsonrpc": "2.0",
                    "method": "template.get",
                    "params": {
                        "output": ["templateid", "name"],
                    },
                    "auth": auth_token,
                    "id": 3
                }

                response = requests.post(ZABBIX_API_URL, json=template_payload, headers=headers)
                templates = response.json()["result"]
                with open("templates.csv", "w", newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow(["Template ID", "Name"])
                    for template in templates:
                        csvwriter.writerow([template["templateid"], template["name"]])

                # Load CSV data into pandas DataFrames
                hostgroups_df = pd.read_csv("hostgroups.csv")
                templates_df = pd.read_csv("templates.csv")

                # Streamlit UI
                st.title("Add Host")

                # Dropdowns for selecting hostgroup and template
                custom_text = st.text_input("Enter the Host Name")

                selected_hostgroup = st.selectbox("Select Hostgroup", [""] + hostgroups_df["Name"].tolist(),key="hstgrp2")
                selected_template = st.selectbox("Select Template", [""] + templates_df["Name"].tolist(),key="temp2")

                if selected_hostgroup and selected_hostgroup != "":
                    selected_hostgroup_id = hostgroups_df[hostgroups_df["Name"] == selected_hostgroup]["Group ID"].values[0]


                if selected_template and selected_template != "":
                    selected_template_id = templates_df[templates_df["Name"] == selected_template]["Template ID"].values[0]


                selected_type = st.selectbox("Select a type", ["Select a type", "1", "2", "3", "4"],key="type")
                if selected_type == "1":
                    st.write("You selected Type 1. This is the output for Type 1.")
                    custom_IP = st.text_input("Enter the IP Name")
                    custom_port = st.text_input("Enter the port number")

                elif selected_type == "2":
                    st.write("You selected Type 2. This is the output for Type 2.")
                    SNMP_type = st.selectbox("Select a SNMP version", ["--", "1", "2", "3"],key="type")
                    if SNMP_type == "1":
                        st.write("Community string is public")
                        st.write("The device has SNMP-V1")
                        snmp_custom_port = st.text_input("Enter the port number")

                    if SNMP_type == "2":
                        st.write("Community string is public")
                        st.write("The device has SNMP-V2")
                        snmp_custom_port = st.text_input("Enter the port number")

                    if SNMP_type == "3":
                        st.write("The device has SNMP-V3")
                        custom_IP = st.text_input("Enter the IP Name")
                        custom_port = st.text_input("Enter the port number")
                        mysecurityname = st.text_input("Enter the security name")


                elif selected_type == "3":
                    st.write("You selected Type 3. This is the output for Type 3.")
                    custom_IP = st.text_input("Enter the IP Name")
                    custom_port = st.text_input("Enter the port number")
                elif selected_type == "4":
                    st.write("You selected Type 4. This is the output for Type 4.")
                    custom_IP = st.text_input("Enter the IP Name")
                    custom_port = st.text_input("Enter the port number")

                if st.button("Enter",key="1"):
                    if selected_type == "1":
                        subprocess.run(["python", "agent_host_add.py", str(selected_hostgroup_id), str(selected_template_id), custom_text,str(custom_IP),str(custom_port)])

                    elif selected_type == "2" and SNMP_type == "3":
                        subprocess.run(["python", "snmpv3_host_add.py", str(selected_hostgroup_id), str(selected_template_id), custom_text,str(custom_IP),str(custom_port),str(mysecurityname)]) 

        if selected == "Multiple Upload":
            uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

            csv_filename = None  # Initialize variable to store the filename

            if uploaded_file is not None:
                csv_filename = uploaded_file.name  # Extract the filename
                st.write(csv_filename)
                df = pd.read_csv(uploaded_file)
                st.dataframe(df)
                execute_button = st.button("Execute",key="2")

                if execute_button:
                    with open(csv_filename, "r") as csvfile:
                        csvreader = csv.reader(csvfile)
                        next(csvreader)  # Skip header row
                        for row in csvreader:
                            selected_type = row[0]
                            selected_hostgroup = row[1]
                            selected_template = row[2]
                            custom_text = row[3]
                            custom_IP = row[4]
                            custom_port = row[5]
                            SNMP_type = row[6]
                            snmp_custom_port = row[7]
                            mysecurityname = row[8]
                            community = row[9]

                            # Capture subprocess output
                            command = []
                            if selected_type == "1":
                                command = ["python", "agent_host_add.py", str(selected_hostgroup), str(selected_template), custom_text, str(custom_IP), str(custom_port)]
                            elif selected_type == "2" and SNMP_type == "3":
                                command = ["python", "snmpv3_host_add.py", str(selected_hostgroup), str(selected_template), custom_text, str(custom_IP), str(snmp_custom_port), str(mysecurityname)]
                            elif selected_type == "2" and SNMP_type == "1":
                                command = ["python", "snmpv1_host_add.py", str(selected_hostgroup), str(selected_template), custom_text, str(custom_IP), str(snmp_custom_port), str(community)]
                            elif selected_type == "2" and SNMP_type == "2":
                                command = ["python", "snmpv2_host_add.py", str(selected_hostgroup), str(selected_template), custom_text, str(custom_IP), str(snmp_custom_port), str(community)]

                            if command:
                                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                stdout, stderr = process.communicate()

                                # Display output in Streamlit UI
                                st.text("Subprocess Output:")
                                st.text(stdout)
                                if stderr:
                                    st.text("Subprocess Error:")
                                    st.text(stderr)

    if menu_id == "Uptimes":
        def convert_image_to_pdf(image_path, output_path):
            try:
                image = Image.open(image_path)
                image_width, image_height = image.size

                increased_pdf_width, increased_pdf_height = portrait((8.3 * inch, 10 * inch))

                scale_factor = min(increased_pdf_width / image_width, increased_pdf_height / 2 / image_height)

                adjusted_width = image_width * scale_factor * 0.9
                adjusted_height = image_height * scale_factor

                x_offset = (increased_pdf_width - adjusted_width) / 2
                y_offset = (increased_pdf_height - adjusted_height) / 2
                c = canvas.Canvas(output_path, pagesize=portrait((8.3 * inch, 10 * inch)))
                c.drawImage(ImageReader(image), x_offset, y_offset, width=adjusted_width, height=adjusted_height)
                c.save()
                print("Image converted to PDF successfully!")
                script_directory = "/home/ubuntu/data"
                script_pdf_path = os.path.join(script_directory, os.path.basename(output_path))
                c = canvas.Canvas(script_pdf_path, pagesize=portrait((8.3 * inch, 10 * inch)))
                c.drawImage(ImageReader(image), x_offset, y_offset, width=adjusted_width, height=adjusted_height)
                c.save()
                print("PDF saved in the script's directory!")

                return output_path
            except Exception as e:
                print("An error occurred:", str(e))
                return None
        def convert_csv_to_pdf(csv_file_path, pdf_output_path, avg_uptime_percentage, avg_downtime_percentage, hostname):
            class PDF(FPDF):
                def __init__(self):
                    super().__init__()
                    self.page_width = 210
                def header(self):
                    self.set_font("Times", "BU", 12)
                    self.cell(0, 10, "Uptime and Downtime Report", align="C", ln=True)
                    self.ln(5)

                def footer(self):
                    pass

                def chapter_title(self, title):
                    self.set_font("Courier", "B", 12)
                    self.cell(0, 10, title, ln=True)

                def chapter_body(self, data):
                    self.set_font("Times", "", 10)
                    self.set_fill_color(255)
                    self.set_text_color(0)
                    self.set_draw_color(0)
                    self.set_line_width(0.3)
                    left_margin = 20
                    right_margin = 20
                    effective_page_width = self.page_width - left_margin - right_margin
                    cell_width = effective_page_width / len(data[0])
                    cell_height = 6

                    self.set_font("Times", "B", 10)
                    for item in data[0]:
                        self.cell(cell_width, cell_height, str(item), border=1, ln=0, align="C", fill=True)
                    self.ln()

                    self.set_font("Times", "", 10)
                    for row in data[1:]:
                        for item in row:
                            self.cell(cell_width, cell_height, str(item), border=1, ln=0, align="C")
                        self.ln()

                    self.ln(10)
                    self.set_font("Times", "B", 12)
                    self.cell(effective_page_width, 10, f"Average Uptime %: {avg_uptime_percentage:.2f}%", border=0, ln=1, align="L")
                    self.cell(effective_page_width, 10, f"Average Downtime % : {avg_downtime_percentage:.2f}%", border=0, ln=1, align="L")

            pdf = PDF()
            pdf.add_page()
            pdf.set_left_margin(20)  
            pdf.set_right_margin(20)  

            with open(csv_file_path, "r") as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader) 
                data = list(reader) 

            pdf.chapter_title(hostname)
            pdf.chapter_body([header] + data)

            pdf.output(pdf_output_path)

            script_directory = "/home/ubuntu/data"
            script_pdf_path = os.path.join(script_directory, os.path.basename(pdf_output_path))
            pdf.output(script_pdf_path)

            return pdf_output_path

        from matplotlib.backends.backend_pdf import PdfPages

        def convert_graph_to_pdf(fig,hostname):
            fig.set_size_inches(8.375, 4)  
            pdf_bytes = io.BytesIO()
            with PdfPages(pdf_bytes) as pdf:
                pdf.savefig(fig, bbox_inches='tight')
            pdf_bytes.seek(0)
            filename=f"2_bar_graph_{hostname}.pdf"
            script_directory = "/home/ubuntu/data"
            script_pdf_path = os.path.join(script_directory, filename)
            with PdfPages(script_pdf_path) as pdf:
                pdf.savefig(fig, bbox_inches='tight')


            return pdf_bytes.getvalue()

        def combine_pdfs_with_watermark(pdfs, margin=20):
            merger = PdfMerger()
            current_date = dt.datetime.now().strftime("%Y-%m-%d")
            watermark_pdf = io.BytesIO()
            c = canvas.Canvas(watermark_pdf, pagesize=letter)
            c.setFont("Helvetica", 50)
            c.rotate(35)
            c.setFillGray(0.1, 0.1) 
            c.drawString(210, 100, "Ishan Technologies") 
            c.rotate(-35) 
            c.setFont("Helvetica", 10)
            c.drawString(33,769, f"Date: {current_date}")
            c.save()
            watermark_pdf.seek(0)

            for pdf in pdfs:
                reader = PdfReader(pdf)
                writer = PdfWriter()
                for page in reader.pages:
                    new_page = PageObject.createBlankPage(width=page.mediaBox.getWidth(),
                                                        height=page.mediaBox.getHeight())
        #
                    watermark_page = PdfReader(watermark_pdf).pages[0]
                    watermark_x_offset = (page.mediaBox.getWidth() - watermark_page.mediaBox.getWidth()) / 2
                    watermark_y_offset = (page.mediaBox.getHeight() - watermark_page.mediaBox.getHeight()) / 2
                    new_page.mergeTranslatedPage(watermark_page, watermark_x_offset, watermark_y_offset)
        #
                    c = canvas.Canvas(io.BytesIO())
                    c.setPageSize((page.mediaBox.getWidth(), page.mediaBox.getHeight()))
                    c.translate(margin, margin)
                    c.setStrokeColorRGB(0, 0, 0)  
                    c.rect(0, 0, page.mediaBox.getWidth() - 2 * margin, page.mediaBox.getHeight() - 2 * margin, stroke=1, fill=0)

                    c.showPage()
                    c.save()
                    outline_page = PdfReader(io.BytesIO(c.getpdfdata())).pages[0]
        #
                    new_page.mergePage(outline_page)
                    new_page.mergePage(page)
        #
                    writer.add_page(new_page)
        #
                merged_pdf = io.BytesIO()
                writer.write(merged_pdf)
                merger.append(merged_pdf)
        #
            merged_pdf = io.BytesIO()
            merger.write(merged_pdf)
            merger.close()
        #
            return merged_pdf

        def combine_pdfs(pdfs):
            merger = PdfMerger()
            for pdf in pdfs:
                merger.append(pdf)
            merged_pdf = io.BytesIO()
            merger.write(merged_pdf)
            merger.close()
            return merged_pdf

        def get_pdf_files_from_folder(folder_path):
            pdf_files = []
            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(folder_path, file_name))
            return sorted(pdf_files)


        def read_csv_data(csv_filename):
            data = []
            with open(csv_filename, 'r') as csvfile:
                csv_reader = csv.reader(csvfile)
                header = next(csv_reader)  
                for row in csv_reader:
                    data.append(row)
            return data

        def read_csv_data_m(inputfile):
            data = []
            with open(inputfile, 'r') as csvfile:
                csv_reader = csv.reader(csvfile)
                header = next(csv_reader) 
                for row in csv_reader:
                    data.append(row)
            return data

        def create_data_table(csv_data):
            if csv_data:
                data_table = [csv_data[0]] + csv_data[1:]  
            else:
                data_table = [["Days", "Downtime%", "Uptime%"], [None, None, None]]
            return data_table

        def calculate_percentage(uptime_percentage, downtime_percentage):
            return uptime_percentage.mean(), downtime_percentage.mean()

        def calculate_duration(start_date):
            return f"{start_date.strftime('%Y-%m-%d')}"

        def group_into_weekly_csv(input_file):
            df = pd.read_csv(input_file)

            df['Days'] = pd.to_datetime(df['Days'], format='%Y-%m-%d', dayfirst=True)

            df = df.sort_values(by='Days', ascending=False)

            output_folder = "weekly_sorted"
            os.makedirs(output_folder, exist_ok=True)

            min_date = df['Days'].min()
            max_date = df['Days'].max()

            current_date = min_date

            durations = []
            up_avgs = []
            down_avgs = []

            while current_date <= max_date:
                group_data = df[(df['Days'] >= current_date) & (df['Days'] < current_date + timedelta(days=7))]
                output_filename = f"{output_folder}/weekly_data_{current_date.strftime('%Y-%m-%d')}_{(current_date + timedelta(days=6)).strftime('%Y-%m-%d')}.csv"
                group_data.to_csv(output_filename, index=False)

                duration = calculate_duration(current_date)
                uptime_percentage = group_data['Uptime%']
                downtime_percentage = group_data['Downtime%']

                up_avg, down_avg = calculate_percentage(uptime_percentage, downtime_percentage)
                durations.append(duration)
                up_avgs.append(up_avg)
                down_avgs.append(down_avg)

                current_date += timedelta(days=7)

            averages_df = pd.DataFrame({
                'Duration': durations,
                'Uptime%': up_avgs,
                'Downtime%': down_avgs
            })

            averages_output_filename = os.path.join(output_folder, "weekly_averages.csv")
            averages_df.to_csv(averages_output_filename, index=False)

            return averages_df


        def create_bar_chart(averages_df):
            sns.set_style("darkgrid")
            custom_colors = ["#8B0000", "#00CED1"]        
            sns.set_palette(custom_colors)

            fig, ax = plt.subplots(figsize=(8, 4))
            dates = averages_df["Duration"]
            downtime_percentages = averages_df["Downtime%"]
            uptime_percentages = averages_df["Uptime%"]

            ax.bar(dates, downtime_percentages, label="Downtime%", alpha=0.7, width=0.4)
            ax.bar(dates, uptime_percentages, bottom=downtime_percentages, label="Uptime%", alpha=0.7, width=0.4)

            ax.set_xlabel("Days", fontsize=10)
            ax.set_ylabel("Percentage", fontsize=10)
            ax.set_title("Uptime and Downtime Report - Weekly", fontsize=12)
            ax.legend(fontsize=10)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.yticks(fontsize=8)

            sns.despine(left=True, bottom=True)

            plt.tight_layout()

            return fig


        ############################################################# Month Section ###############################################################
        def create_output_folder(folder_name):
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)


        def separate_csv_by_month(input_file, output_folder):
            data = pd.read_csv(input_file, parse_dates=['Days'], dayfirst=True, infer_datetime_format=False)

            data['Days'] = pd.to_datetime(data['Days'], format="%Y-%m-%d")

            print(data['Days'].dtype)
            print(data['Days'].head())

            grouped_data = data.groupby(data['Days'].dt.month)    
            for month, month_data in grouped_data:
                year = datetime.now().strftime("%Y")
                output_file = os.path.join(output_folder, f'month_{month:02d}_{year}.csv')
                month_data.to_csv(output_file, index=False)

        def calculate_avg_values(input_folder, output_folder):
            all_data = []
            for filename in os.listdir(input_folder):
                if filename.startswith("month_") and filename.endswith(".csv"):
                    file_path = os.path.join(input_folder, filename)
                    month_data = pd.read_csv(file_path)

                    avg_uptime = month_data["Uptime%"].mean()
                    avg_downtime = month_data["Downtime%"].mean()

                    filename_parts = filename.split("_")[1].split(".")[0].split("-")
                    if len(filename_parts) == 2:
                        month, year = filename_parts
                        month = int(month)
                        year = int(year)
                    else:
                        month = int(filename_parts[0])
                        year = datetime.now().year 

                    all_data.append({"Duration": f"{month}-{year}", "Up_Avg": avg_uptime, "Down_Avg": avg_downtime})

            avg_df = pd.DataFrame(all_data)

            avg_output_csv = os.path.join(output_folder, "average_values.csv")
            avg_df.to_csv(avg_output_csv, index=False)

        def create_bar_chart_m(averages_df):
            sns.set_style("darkgrid")
            custom_colors = ["#8B0000", "#00CED1"]
            sns.set_palette(custom_colors)

            fig, ax = plt.subplots(figsize=(8, 4))

            averages_df = averages_df.sort_values("Duration")

            dates = averages_df["Duration"]
            up_avg_values = averages_df["Up_Avg"]
            down_avg_values = averages_df["Down_Avg"]

            ax.bar(dates, down_avg_values, label="Downtime%", alpha=0.7, width=0.4)
            ax.bar(dates, up_avg_values, bottom=down_avg_values, label="Uptime%", alpha=0.7, width=0.4)

            ax.set_xlabel("Duration", fontsize=10)
            ax.set_ylabel("Percentage", fontsize=10)
            ax.set_title("Uptime and Downtime Report - Monthly", fontsize=12)
            ax.legend(fontsize=10)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.yticks(fontsize=8)

            sns.despine(left=True, bottom=True)

            plt.tight_layout()

            return fig
        data = pd.read_csv('file.csv')

        # Get unique hostgroup names
        hostgroups = data['hostgroup'].unique()


        col1, col2 = st.columns([1, 2.5]) 

        with col1 :
            selected_hostgroup = st.selectbox('Select Hostgroup', [' - '] + list(hostgroups),key="hg5")

            # Filter data based on selected hostgroup
            filtered_data = data[data['hostgroup'] == selected_hostgroup] if selected_hostgroup != ' - ' else data

            # Get unique hostnames within the selected hostgroup
            hostnames = filtered_data['hostname'].unique()

            # Hostname selectbox
            selected_hostname = st.selectbox('Select Hostname', [' - '] + list(hostnames),key="hn5")

            hostname=selected_hostname


            selected_date = st.date_input("Select Date",key="Date1")

            # Set the initial time to 00:00:00
            initial_time = datetime.strptime("00:00:00", "%H:%M:%S").time()

            # Set the initial time to the current time
            current_time = datetime.now().time()

            # Create separate input boxes for hours, minutes, and seconds for the first time_value input
            col3, col4, col5 = st.columns(3)
            selected_hour = col3.number_input("", min_value=0, max_value=23, value=initial_time.hour, key="hour1")
            selected_minute = col4.number_input("", min_value=0, max_value=59, value=initial_time.minute, key="minute1")
            selected_second = col5.number_input("", min_value=0, max_value=59, value=initial_time.second, key="second1")

            # Combine the selected date and time for the first time_value input
            time_value = datetime.combine(selected_date, time(selected_hour, selected_minute, selected_second))

            selected_date2 = st.date_input("Select Date",key="Date2")

            # Create separate input boxes for hours, minutes, and seconds for the second time_value input
            col6, col7, col8 = st.columns(3)
            selected_hour2 = col6.number_input("", min_value=0, max_value=23, value=current_time.hour, key="hour2")
            selected_minute2 = col7.number_input("", min_value=0, max_value=59, value=current_time.minute, key="minute2")
            selected_second2 = col8.number_input("", min_value=0, max_value=59, value=current_time.second, key="second2")

            # Combine the selected date and time for the second time_value input
            time_value2 = datetime.combine(selected_date2, time(selected_hour2, selected_minute2, selected_second2))
            if st.button("Get Uptime",key="3"):
                with col2:
                    start_timestamp = int(time_value.timestamp())
                    end_timestamp = int(time_value2.timestamp())
                    duration_in_seconds = end_timestamp - start_timestamp

                    duration_in_days = duration_in_seconds / 86400

                    conn = psycopg2.connect(database="zabbix_db1", user="zabbixuser", password="zabbixpass", host="18.222.141.167", port="5432")
                    cursor = conn.cursor()

                    query = """
                        SELECT DISTINCT
                            problem.objectid,
                            TO_CHAR(TO_TIMESTAMP(problem.clock), 'YYYY-MM-DD HH24:MI:SS') AS start_time,
                            triggers.description AS problem_description,
                            r.eventid AS r_eventid,
                            TO_CHAR(TO_TIMESTAMP(COALESCE(r.clock, EXTRACT(EPOCH FROM NOW()))), 'YYYY-MM-DD HH24:MI:SS') AS end_time,
                            CASE
                                WHEN r.clock IS NOT NULL
                                    THEN (EXTRACT(EPOCH FROM TO_TIMESTAMP(r.clock)) - EXTRACT(EPOCH FROM TO_TIMESTAMP(problem.clock)))
                                ELSE NULL
                            END AS duration,
                            hosts.host AS hostname
                        FROM
                            events problem
                            JOIN triggers ON triggers.triggerid = problem.objectid
                            LEFT JOIN events r ON r.objectid = problem.objectid AND r.value = 0 AND r.clock > problem.clock
                                AND NOT EXISTS (
                                    SELECT 1 FROM events r2
                                    WHERE r2.objectid = r.objectid AND r2.value = 0 AND r2.clock > problem.clock AND r2.clock < r.clock
                                )
                            LEFT JOIN functions f ON triggers.triggerid = f.triggerid
                            LEFT JOIN items i ON f.itemid = i.itemid
                            LEFT JOIN hosts ON i.hostid = hosts.hostid
                        WHERE
                            problem.object = 0
                            AND problem.clock <= %s
                            AND problem.value = 1
                    """

                    query += f"AND hosts.host = '{selected_hostname}' "
                    query += "AND i.key_ = 'icmpping'"

                    cursor.execute(query,(end_timestamp,))

                    rows = cursor.fetchall()

                    cursor.close()
                    conn.close()

                    downtime_per_day = {}
                    for row in rows:
                        start_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S') 
                        end_time = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S')  

                        start_date = start_time.date()
                        end_date = end_time.date() 

                        if start_date == end_date:
                            duration = (end_time - start_time).total_seconds() 
                            downtime_per_day[start_date] = downtime_per_day.get(start_date, 0) + duration
                        else:
                            next_day_start = datetime.combine(start_date + timedelta(days=1), datetime.min.time())
                            duration = (next_day_start - start_time).total_seconds() 
                            downtime_per_day[start_date] = downtime_per_day.get(start_date, 0) + duration

                            intermediate_date = start_date + timedelta(days=1)
                            while intermediate_date != end_date:
                                next_day_start = datetime.combine(intermediate_date + timedelta(days=1), datetime.min.time())
                                duration = (next_day_start - datetime.combine(intermediate_date, datetime.min.time())).total_seconds()  
                                downtime_per_day[intermediate_date] = downtime_per_day.get(intermediate_date, 0) + duration
                                intermediate_date += timedelta(days=1)

                            duration = (end_time - datetime.combine(end_date, datetime.min.time())).total_seconds() 
                            downtime_per_day[end_date] = downtime_per_day.get(end_date, 0) + duration

                    start_date = time_value.date() 
                    end_date = time_value2.date()

                    csv_data = []
                    current_date = start_date
                    downtime_percentages = []
                    uptime_percentages = []
                    while current_date <= end_date:
                        downtime = downtime_per_day.get(current_date, 0)
                        downtime_value = int(downtime)
                        downtime_percentage = (downtime / (24 * 60 * 60)) * 100 
                        uptime_percentage = 100 - downtime_percentage 

                        csv_data.append([current_date, downtime_percentage, uptime_percentage])
                        downtime_percentages.append(downtime_percentage)
                        uptime_percentages.append(uptime_percentage)
                        current_date += timedelta(days=1)
                    total_downtime_percentage = sum(downtime_percentages) / len(downtime_percentages)
                    total_uptime_percentage = sum(uptime_percentages) / len(uptime_percentages)
                    avg_downtime_percentage = sum(downtime_percentages) / len(downtime_percentages)
                    avg_uptime_percentage = 100 - avg_downtime_percentage
                    csv_filename = f"downtime_report_{hostname}.csv"
                    with open(csv_filename, mode="w", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow(["Days", "Downtime%", "Uptime%"]) 
                        writer.writerows(csv_data)
                    csv_df = pd.DataFrame(csv_data)

                    csv_string = csv_df.to_csv(index=False)

                    csv_filename = f"downtime_report_{hostname}.csv"
                    b64 = base64.b64encode(csv_string.encode()).decode()
                    href = f'<a href="data:text/csv;charset=utf-8;base64,{b64}" download="{csv_filename}">Download CSV ({hostname})</a>'
                    st.markdown(f"Download the CSV file: {href}", unsafe_allow_html=True)
                    if duration_in_days <= 31:
                        csv_data = read_csv_data(csv_filename)

                        column_names = ["Days", "Downtime%", "Uptime%"]
                    #                        df = pd.DataFrame(csv_data[1:], columns=column_names)
                    #                        st.dataframe(df,height=400,width=800)

                        df = pd.read_csv(csv_filename)
                        st.dataframe(df,height=400,width=800)

                        st.write(f"Average Downtime: {avg_downtime_percentage:.2f}%")
                        st.write(f"Average Uptime: {avg_uptime_percentage:.2f}%")

                        df = pd.read_csv(csv_filename)

                        dates = df["Days"]
                        downtime_percentages = df["Downtime%"]
                        uptime_percentages = df["Uptime%"]

                        sns.set_style("darkgrid")
                        custom_colors = ["#8B0000", "#00CED1"]
                        sns.set_palette(custom_colors)

                        fig, ax = plt.subplots(figsize=(8, 4))

                        ax.bar(dates, downtime_percentages, label="Downtime%", alpha=0.7, width=0.4)
                        ax.bar(dates, uptime_percentages, bottom=downtime_percentages, label="Uptime%", alpha=0.7, width=0.4)
                        ax.set_xlabel("Days", fontsize=10)
                        ax.set_ylabel("Percentage", fontsize=10)
                        ax.set_title("Uptime and Downtime Report - Daily", fontsize=12)
                        ax.legend(fontsize=10)
                        plt.xticks(rotation=45, ha='right', fontsize=8)
                        plt.yticks(fontsize=8)

                        sns.despine(left=True, bottom=True)

                        plt.tight_layout()
                        plt.show()
                        st.pyplot(fig)

                        pdf_content_bar = convert_graph_to_pdf(fig,hostname)

                        pdf_filename_bar = f"bar_graph_{hostname}.pdf"
                        b64_pdf = base64.b64encode(pdf_content_bar).decode()
                        href_pdf = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename_bar}" class="button"><i class="fas fa-download" style="color: black;"></i> Bar_Chart PDF</a>'


                        st.markdown(f"{href_pdf}", unsafe_allow_html=True)

                        csv_filepath = os.path.join(".", csv_filename)

                        pdf_filename = f"1_downtime_report_{hostname}.pdf"
                        pdf_filepath = os.path.join("/home/ubuntu/data", pdf_filename)
                        convert_csv_to_pdf(csv_filepath, pdf_filepath, avg_uptime_percentage, avg_downtime_percentage, hostname)

                        with open(pdf_filepath, "rb") as pdf_file:
                            pdf_content = pdf_file.read()
                            b64_pdf = base64.b64encode(pdf_content).decode("utf-8")
                            download_pdf_button_html = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" class="button"><i class="fas fa-download" style="color: black;"></i> Up_Down PDF</a>'
                            st.markdown(download_pdf_button_html, unsafe_allow_html=True)
                    elif 31 < duration_in_days < 182:
                        duration_in_weeks = duration_in_days / 7
                        averages_df = group_into_weekly_csv(csv_filename)

                        csv_data = read_csv_data_m("/home/ubuntu/weekly_sorted/weekly_averages.csv")



                        column_names = ["Days", "Uptime%", "Downtime%"]
                        df = pd.DataFrame(csv_data, columns=column_names)
                        st.dataframe(df,height=400,width=800)


                        fig = create_bar_chart(averages_df)
                        st.pyplot(fig)
                        pdf_bytes = convert_graph_to_pdf(fig, hostname)
                        st.download_button(
                            label="Download as PDF",
                            data=pdf_bytes,
                            file_name=f"bar_graph_{hostname}.pdf",
                            mime="application/pdf"
                        )
                        csv_filepath = os.path.join(".", csv_filename)

                        pdf_filename = f"1_downtime_report_{hostname}.pdf"
                        pdf_filepath = os.path.join("/home/ubuntu/data", pdf_filename)
                        convert_csv_to_pdf(csv_filepath, pdf_filepath, avg_uptime_percentage, avg_downtime_percentage,hostname)

                        with open(pdf_filepath, "rb") as pdf_file:
                            pdf_content = pdf_file.read()
                            b64_pdf = base64.b64encode(pdf_content).decode("utf-8")
                            download_pdf_button_html = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" class="button"><i class="fas fa-download" style="color: black;"></i> Up_Down PDF</a>'
                            st.markdown(download_pdf_button_html, unsafe_allow_html=True)

                    else:
                        input_csv_file = csv_filename
                        output_folder_name = "output_files"

                        create_output_folder(output_folder_name)
                        separate_csv_by_month(input_csv_file, output_folder_name)
                        calculate_avg_values(output_folder_name, output_folder_name)

                        averages_df = pd.read_csv(os.path.join(output_folder_name, "average_values.csv"))
                        csv_data = read_csv_data_m("/home/ubuntu/output_files/average_values.csv")



                        column_names = ["Days", "Uptime%", "Downtime%"]
                        df = pd.DataFrame(csv_data, columns=column_names)
                        st.dataframe(df,height=400,width=800)


                        fig = create_bar_chart_m(averages_df)
                        st.pyplot(fig)

                        pdf_bytes = convert_graph_to_pdf(fig, hostname)
                        st.download_button(
                            label="Download Bar Chart as PDF",
                            data=pdf_bytes,
                            file_name="bar_chart.pdf",
                            mime="application/pdf"
                        )
                        csv_filepath = os.path.join(".", csv_filename)
                        pdf_filename = f"1_downtime_report_{hostname}.pdf"
                        pdf_filepath = os.path.join("/home/ubuntu/data", pdf_filename)
                        convert_csv_to_pdf(csv_filepath, pdf_filepath, avg_uptime_percentage, avg_downtime_percentage,hostname)

                        with open(pdf_filepath, "rb") as pdf_file:
                            pdf_content = pdf_file.read()
                            b64_pdf = base64.b64encode(pdf_content).decode("utf-8")
                            download_pdf_button_html = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" class="button"><i class="fas fa-download" style="color: black;"></i> Up_Down PDF</a>'
                            st.markdown(download_pdf_button_html, unsafe_allow_html=True)

                    st.markdown("PDF files to combine:")
                    folder_path = "/home/ubuntu/data"

                    if st.button("Combine",key="4"):
                        if not folder_path:
                            st.warning("Please enter the folder path.")
                        else:
                            pdf_files = get_pdf_files_from_folder(folder_path)
                        if not pdf_files:
                            st.warning("No PDF files found in the specified folder.")
                        else:
                            merged_pdf = combine_pdfs_with_watermark(pdf_files)
                        st.success("PDF files combined successfully! You can download the combined PDF below.")
                        st.download_button("Download Combined PDF", data=merged_pdf, file_name="combined_pdf.pdf", mime="application/pdf")

    if menu_id == "subid11":
        ZABBIX_API_URL =  "http://18.222.141.167:8080/api_jsonrpc.php"
        UNAME = "Zabbix"
        PWORD = "Paramaah@@123"

        # Authenticate the user and obtain the authentication token
        r = requests.post(ZABBIX_API_URL,
                        json={
                            "jsonrpc": "2.0",
                            "method": "user.login",
                            "params": {
                                "user": UNAME,
                                "password": PWORD
                            },
                            "id": 1
                        })

        AUTHTOKEN = r.json()["result"]

        # Retrieve a list of hosts with additional details
        r = requests.post(ZABBIX_API_URL,
                        json={
                            "jsonrpc": "2.0",
                            "method": "host.get",
                            "params": {
                                "output": [
                                    "hostid",
                                    "host",
                                    "groups",
                                    "parentTemplates",
                                    "status",
                                    "proxy_hostid"
                                ],
                                "selectGroups": "extend",
                                "selectParentTemplates": ["templateid", "name"],
                                "selectInterfaces": ["ip"]
                            },
                            "auth": AUTHTOKEN,
                            "id": 2
                        })

        hosts_data = r.json()["result"]

        # Create a list to store the data
        data = []

        # Retrieve the IP addresses, host group, templates, monitoring source, and monitored status for each host
        for host in hosts_data:
            host_id = host["hostid"]
            hostname = host["host"]
            ip_data = host["interfaces"]
            groups = host["groups"]
            templates = host["parentTemplates"]
            monitored = host["status"] == "0"
            proxy_hostid = host["proxy_hostid"]

            # Extract IP addresses
            ip_addresses = [ip["ip"] for ip in ip_data]

            # Extract host group names
            group_names = [group["name"] for group in groups]

            # Extract template names
            template_names = [template["name"] for template in templates]

            # Determine monitoring source
            monitoring_source = "Server" if proxy_hostid == "0" else "Proxy"

            # Append data to the list
            data.append({
                "Hostname": hostname,
                "Host ID": host_id,
                "IP Addresses": ", ".join(ip_addresses),
                "Host Groups": ", ".join(group_names),
                "Templates": ", ".join(template_names),
                "Monitoring Source": monitoring_source,
                "Monitored": "Yes" if monitored else "No"
            })

        # Convert the data to a DataFrame
        df = pd.DataFrame(data)

        # Get unique host groups
        unique_host_groups = sorted(df["Host Groups"].explode().unique())

        # Streamlit app
        st.title("Zabbix Host Details")

        # Host group filter dropdown
        selected_host_group = st.selectbox("Select Host Group", ["All"] + unique_host_groups,key="unique_hg")

        # Apply host group filter
        if selected_host_group != "All":
            filtered_df = df[df["Host Groups"].apply(lambda x: selected_host_group in x)]
            total_hosts = len(filtered_df)
        else:
            filtered_df = df
            total_hosts = len(df)
        # Layout setup
        col1, col2 = st.columns([2.5, 1])  # Adjust the ratio as needed

        # Display table
        col1.dataframe(filtered_df, width=1200, height=820)  # Adjust width as needed

        with col2 :   
            total_hosts = len(filtered_df)
            st.info(f"Total Hosts: {total_hosts}")
            col3,col4 = st.columns(2)

            csv_buffer = BytesIO()
            filtered_df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            b64 = base64.b64encode(csv_buffer.read()).decode()
            col3.download_button("Download CSV File", data=csv_buffer, file_name="filtered_data.csv", key="csv")

            pdf_buffer = BytesIO()
            pdf = filtered_df.to_markdown()
            pdf_buffer.write(pdf.encode('utf-8'))
            pdf_buffer.seek(0)
            b64 = base64.b64encode(pdf_buffer.read()).decode()
            col4.download_button("Download PDF File", data=pdf_buffer, file_name="filtered_data.pdf", key="pdf")


            # Create a pie chart for monitoring sources
            monitoring_counts = filtered_df["Monitoring Source"].value_counts()
            fig, ax = plt.subplots()
            ax.pie(monitoring_counts, labels=monitoring_counts.index, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
            ax.set_title("Distribution of Monitoring Sources")  # Add title to the pie chart
            st.pyplot(fig)

            monitoring_status_counts = filtered_df["Monitored"].value_counts()
            fig, ax = plt.subplots()
            ax.pie(monitoring_status_counts, labels=monitoring_status_counts.index, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
            ax.set_title("Monitoring Status")  # Add title to the pie chart
            st.pyplot(fig)

        # Logout the user
        r = requests.post(ZABBIX_API_URL,
                        json={
                            "jsonrpc": "2.0",
                            "method": "user.logout",
                            "params": {},
                            "auth": AUTHTOKEN,
                            "id": 3
                        })

    if menu_id == "Uptime Reports":
        st.title("Uptime Report UI")
        add_logo('Ishan technologies Logo Uniquely Yours.png', height=80)


        def get_graphs(search_text, zabbix_url, zabbix_user, zabbix_password):

            auth_data = {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {"user": zabbix_user, "password": zabbix_password},
                "id": 1,
            }
            response = requests.post(zabbix_url, json=auth_data)
            result = response.json()
            auth_token = result["result"]


            search_data = {
                "jsonrpc": "2.0",
                "method": "graph.get",
                "params": {
                    "output": ["name", "graphid"],
                    "search": {"name": search_text},
                },
                "auth": auth_token,
                "id": 2,
            }
            response = requests.post(zabbix_url, json=search_data)
            result = response.json()
            graphs = result["result"]


            logout_data = {
                "jsonrpc": "2.0",
                "method": "user.logout",
                "params": [],
                "auth": auth_token,
                "id": 3,
            }
            requests.post(zabbix_url, json=logout_data)

            return graphs

        def search_zabbix_hostnames(search_text, zabbix_url, zabbix_user, zabbix_password):
            # Create session
            session = requests.Session()
            session.headers.update({'Content-Type': 'application/json'})

            # Log in to Zabbix API
            login_payload = {
                'jsonrpc': '2.0',
                'method': 'user.login',
                'params': {
                    'user': zabbix_user,
                    'password': zabbix_password
                },
                'id': 1
            }
            response = session.post(zabbix_url, json=login_payload)
            auth_token = response.json()['result']

            # Search for hostnames
            search_payload = {
                'jsonrpc': '2.0',
                'method': 'host.get',
                'params': {
                    'output': ['host'],
                    'search': {'name': search_text}
                },
                'auth': auth_token,
                'id': 2
            }
            response = session.post(zabbix_url, json=search_payload)
            hosts = response.json()['result']

            # Log out from Zabbix API
            logout_payload = {
                'jsonrpc': '2.0',
                'method': 'user.logout',
                'params': [],
                'auth': auth_token,
                'id': 3
            }
            session.post(zabbix_url, json=logout_payload)

            return [host['host'] for host in hosts]


        def convert_image_to_pdf(image_path, output_path):
            try:
                image = Image.open(image_path)
                image_width, image_height = image.size

                increased_pdf_width, increased_pdf_height = portrait((8.3 * inch, 10 * inch))

                scale_factor = min(increased_pdf_width / image_width, increased_pdf_height / 2 / image_height)

                adjusted_width = image_width * scale_factor * 0.9
                adjusted_height = image_height * scale_factor

                x_offset = (increased_pdf_width - adjusted_width) / 2
                y_offset = (increased_pdf_height - adjusted_height) / 2
                c = canvas.Canvas(output_path, pagesize=portrait((8.3 * inch, 10 * inch)))
                c.drawImage(ImageReader(image), x_offset, y_offset, width=adjusted_width, height=adjusted_height)
                c.save()
                print("Image converted to PDF successfully!")
                script_directory = "/home/ubuntu/data"
                script_pdf_path = os.path.join(script_directory, os.path.basename(output_path))
                c = canvas.Canvas(script_pdf_path, pagesize=portrait((8.3 * inch, 10 * inch)))
                c.drawImage(ImageReader(image), x_offset, y_offset, width=adjusted_width, height=adjusted_height)
                c.save()
                print("PDF saved in the script's directory!")

                return output_path
            except Exception as e:
                print("An error occurred:", str(e))
                return None


        #    def convert_image_to_pdf(image_path, output_path):
        #        try:
        #            image = Image.open(image_path)
        #            image_width, image_height = image.size
        #            pdf_width, pdf_height = portrait((8 * inch, 8 * inch))
        #            scale_factor = min(pdf_width / image_width, pdf_height / 2 / image_height)
        #            adjusted_width = image_width * scale_factor * 0.9
        #            adjusted_height = image_height * scale_factor
        #            x_offset = (pdf_width - adjusted_width) / 2
        #            y_offset = (pdf_height - adjusted_height) / 2
        #            c = canvas.Canvas(output_path, pagesize=portrait((8 * inch, 8 * inch)))
        #            c.drawImage(ImageReader(image), x_offset, y_offset, width=adjusted_width, height=adjusted_height)
        #            c.save()
        #            print("Image converted to PDF successfully!")
        #            script_directory = "/home/ubuntu/data"
        #            script_pdf_path = os.path.join(script_directory, os.path.basename(output_path))
        #            c = canvas.Canvas(script_pdf_path, pagesize=portrait((8 * inch, 8 * inch)))
        #            c.drawImage(ImageReader(image), x_offset, y_offset, width=adjusted_width, height=adjusted_height)
        #            c.save()
        #            print("PDF saved in the script's directory!")

        #            return output_path
        #        except Exception as e:
        #            print("An error occurred:", str(e))
        #            return None

        from fpdf import FPDF

        def convert_csv_to_pdf(csv_file_path, pdf_output_path, avg_uptime_percentage, avg_downtime_percentage, hostname):
            class PDF(FPDF):
                def __init__(self):
                    super().__init__()
                    self.page_width = 210
                def header(self):
                    self.set_font("Times", "BU", 12)
                    self.cell(0, 10, "Uptime and Downtime Report", align="C", ln=True)
                    self.ln(5)

                def footer(self):
                    pass

                def chapter_title(self, title):
                    self.set_font("Courier", "B", 12)
                    self.cell(0, 10, title, ln=True)

                def chapter_body(self, data):
                    self.set_font("Times", "", 10)
                    self.set_fill_color(255)
                    self.set_text_color(0)
                    self.set_draw_color(0)
                    self.set_line_width(0.3)
                    left_margin = 20
                    right_margin = 20
                    effective_page_width = self.page_width - left_margin - right_margin
                    cell_width = effective_page_width / len(data[0])
                    cell_height = 6

                    self.set_font("Times", "B", 10)
                    for item in data[0]:
                        self.cell(cell_width, cell_height, str(item), border=1, ln=0, align="C", fill=True)
                    self.ln()

                    self.set_font("Times", "", 10)
                    for row in data[1:]:
                        for item in row:
                            self.cell(cell_width, cell_height, str(item), border=1, ln=0, align="C")
                        self.ln()

                    self.ln(10)
                    self.set_font("Times", "B", 12)
                    self.cell(effective_page_width, 10, f"Average Uptime %: {avg_uptime_percentage:.2f}%", border=0, ln=1, align="L")
                    self.cell(effective_page_width, 10, f"Average Downtime % : {avg_downtime_percentage:.2f}%", border=0, ln=1, align="L")

            pdf = PDF()
            pdf.add_page()
            pdf.set_left_margin(20)  
            pdf.set_right_margin(20)  

            with open(csv_file_path, "r") as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader) 
                data = list(reader) 

            pdf.chapter_title(hostname)
            pdf.chapter_body([header] + data)

            pdf.output(pdf_output_path)

            script_directory = "/home/ubuntu/data"
            script_pdf_path = os.path.join(script_directory, os.path.basename(pdf_output_path))
            pdf.output(script_pdf_path)

            return pdf_output_path


        def download_graphs(search_text, zabbix_url, zabbix_user, zabbix_password, time_value1, time_value2,col2):
            graphs = get_graphs(search_text, zabbix_url, zabbix_user, zabbix_password)

            output_file = "zabbix_graphs.csv"
            with open(output_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Graph ID", "Graph Name"])
                writer.writerows([[graph["graphid"], graph["name"]] for graph in graphs])

            col2.success(f"Graph names and IDs matching '{search_text}' saved to {output_file}.")

            graph_id = None
            graph_name = None
            with open(output_file, "r") as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  
                for row in reader:
                    graph_id, graph_name = row
                    break  

            if graph_id is None:
                col2.warning("Graph ID not found in the CSV file.")
        #            logoname = f"1_aishanlogo.jpg"
        #            logo_output_path = f"1_aishanlogo.pdf"
        #            logo_output_path = convert_image_to_pdf(logoname, logo_output_path)
                return

            filename = f"graph_{graph_id}.png"

            bash_cmd = f"./ishan.sh {graph_id} \"{time_value1}\" \"{time_value2}\" {filename}"
            subprocess.run(bash_cmd, shell=True, capture_output=True)

            col2.success("Graph downloaded successfully!")
            graph_content = open(filename, "rb").read()
            col2.image(graph_content, caption="Downloaded Graph", use_column_width=True)

            pdf_output_path = f"graph_{graph_id}.pdf"
            pdf_output_path = convert_image_to_pdf(filename, pdf_output_path)
            
        #        logoname = f"1_aishanlogo.jpg"
        #        logo_output_path = f"1_aishanlogo.pdf"
        #        logo_output_path = convert_image_to_pdf(logoname, logo_output_path)

            if pdf_output_path:
                with open(pdf_output_path, "rb") as pdf_file:
                    pdf_content = pdf_file.read()
                    b64_pdf = base64.b64encode(pdf_content).decode("utf-8")
                    download_pdf_button_html = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_output_path}" class="button"><i class="fas fa-download" style="color: black;"></i> Download PDF</a>'
                    col2.markdown(download_pdf_button_html, unsafe_allow_html=True)

            os.remove(filename)
        from matplotlib.backends.backend_pdf import PdfPages

        def convert_graph_to_pdf(fig,hostname):
            fig.set_size_inches(8.375, 4)  
            pdf_bytes = io.BytesIO()
            with PdfPages(pdf_bytes) as pdf:
                pdf.savefig(fig, bbox_inches='tight')
            pdf_bytes.seek(0)
            filename=f"2_bar_graph_{hostname}.pdf"
            script_directory = "/home/ubuntu/data"
            script_pdf_path = os.path.join(script_directory, filename)
            with PdfPages(script_pdf_path) as pdf:
                pdf.savefig(fig, bbox_inches='tight')


            return pdf_bytes.getvalue()

        def combine_pdfs_with_watermark(pdfs, margin=20):
            merger = PdfMerger()
            current_date = dt.datetime.now().strftime("%Y-%m-%d")
            watermark_pdf = io.BytesIO()
            c = canvas.Canvas(watermark_pdf, pagesize=letter)
            c.setFont("Helvetica", 50)
            c.rotate(35)
            c.setFillGray(0.1, 0.1) 
            c.drawString(210, 100, "Ishan Technologies") 
            c.rotate(-35) 
            c.setFont("Helvetica", 10)
            c.drawString(33,769, f"Date: {current_date}")
            c.save()
            watermark_pdf.seek(0)
        #        logo_path = "1_aishanlogo.jpg"
        #        logo_image = ImageReader(logo_path)

            for pdf in pdfs:
                reader = PdfReader(pdf)
                writer = PdfWriter()
        #            for page_num, page in enumerate(reader.pages, start=1):
                for page in reader.pages:
                    new_page = PageObject.createBlankPage(width=page.mediaBox.getWidth(),
                                                        height=page.mediaBox.getHeight())
        #
                    watermark_page = PdfReader(watermark_pdf).pages[0]
                    watermark_x_offset = (page.mediaBox.getWidth() - watermark_page.mediaBox.getWidth()) / 2
                    watermark_y_offset = (page.mediaBox.getHeight() - watermark_page.mediaBox.getHeight()) / 2
                    new_page.mergeTranslatedPage(watermark_page, watermark_x_offset, watermark_y_offset)
        #
                    c = canvas.Canvas(io.BytesIO())
                    c.setPageSize((page.mediaBox.getWidth(), page.mediaBox.getHeight()))
                    c.translate(margin, margin)
                    c.setStrokeColorRGB(0, 0, 0)  
                    c.rect(0, 0, page.mediaBox.getWidth() - 2 * margin, page.mediaBox.getHeight() - 2 * margin, stroke=1, fill=0)
        #                c.rect(margin, margin, page.mediaBox.getWidth() - 2 * margin, page.mediaBox.getHeight() - 2 * margin, stroke=1, fill=0)
        #                logo_x_offset = float(page.mediaBox.getWidth()) - 100 - margin
        #                logo_y_offset = float(page.mediaBox.getHeight()) - 50 - margin
        #                c.drawImage(logo_image, float(page.mediaBox.getWidth()) - 100, float(page.mediaBox.getHeight()) - 50, width=80, height=40)

        #                c.drawImage(logo_image, logo_x_offset, logo_y_offset, width=80, height=40)
                    c.showPage()
                    c.save()
                    outline_page = PdfReader(io.BytesIO(c.getpdfdata())).pages[0]
        #
                    new_page.mergePage(outline_page)
                    new_page.mergePage(page)
        #
                    writer.add_page(new_page)
        #
                merged_pdf = io.BytesIO()
                writer.write(merged_pdf)
                merger.append(merged_pdf)
        #
            merged_pdf = io.BytesIO()
            merger.write(merged_pdf)
            merger.close()
        #
            return merged_pdf

        def combine_pdfs(pdfs):
            merger = PdfMerger()
            for pdf in pdfs:
                merger.append(pdf)
            merged_pdf = io.BytesIO()
            merger.write(merged_pdf)
            merger.close()
            return merged_pdf

        def get_pdf_files_from_folder(folder_path):
            pdf_files = []
            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(folder_path, file_name))
            return sorted(pdf_files)


        def read_csv_data(csv_filename):
            data = []
            with open(csv_filename, 'r') as csvfile:
                csv_reader = csv.reader(csvfile)
                header = next(csv_reader)  
                for row in csv_reader:
                    data.append(row)
            return data

        def read_csv_data_m(inputfile):
            data = []
            with open(inputfile, 'r') as csvfile:
                csv_reader = csv.reader(csvfile)
                header = next(csv_reader) 
                for row in csv_reader:
                    data.append(row)
            return data

        def create_data_table(csv_data):
            if csv_data:
                data_table = [csv_data[0]] + csv_data[1:]  
            else:
                data_table = [["Days", "Downtime%", "Uptime%"], [None, None, None]]
            return data_table


        def calculate_percentage(uptime_percentage, downtime_percentage):
            return uptime_percentage.mean(), downtime_percentage.mean()

        def calculate_duration(start_date):
            return f"{start_date.strftime('%Y-%m-%d')}"

        def group_into_weekly_csv(input_file):
            df = pd.read_csv(input_file)

            df['Days'] = pd.to_datetime(df['Days'], format='%Y-%m-%d', dayfirst=True)

            df = df.sort_values(by='Days', ascending=False)

            output_folder = "weekly_sorted"
            os.makedirs(output_folder, exist_ok=True)

            min_date = df['Days'].min()
            max_date = df['Days'].max()

            current_date = min_date

            durations = []
            up_avgs = []
            down_avgs = []

            while current_date <= max_date:
                group_data = df[(df['Days'] >= current_date) & (df['Days'] < current_date + timedelta(days=7))]
                output_filename = f"{output_folder}/weekly_data_{current_date.strftime('%Y-%m-%d')}_{(current_date + timedelta(days=6)).strftime('%Y-%m-%d')}.csv"
                group_data.to_csv(output_filename, index=False)

                duration = calculate_duration(current_date)
                uptime_percentage = group_data['Uptime%']
                downtime_percentage = group_data['Downtime%']

                up_avg, down_avg = calculate_percentage(uptime_percentage, downtime_percentage)
                durations.append(duration)
                up_avgs.append(up_avg)
                down_avgs.append(down_avg)

                current_date += timedelta(days=7)

            averages_df = pd.DataFrame({
                'Duration': durations,
                'Uptime%': up_avgs,
                'Downtime%': down_avgs
            })

            averages_output_filename = os.path.join(output_folder, "weekly_averages.csv")
            averages_df.to_csv(averages_output_filename, index=False)

            return averages_df


        def create_bar_chart(averages_df):
            sns.set_style("darkgrid")
            custom_colors = ["#8B0000", "#00CED1"]        
            sns.set_palette(custom_colors)

            fig, ax = plt.subplots(figsize=(8, 4))
            dates = averages_df["Duration"]
            downtime_percentages = averages_df["Downtime%"]
            uptime_percentages = averages_df["Uptime%"]

            ax.bar(dates, downtime_percentages, label="Downtime%", alpha=0.7, width=0.4)
            ax.bar(dates, uptime_percentages, bottom=downtime_percentages, label="Uptime%", alpha=0.7, width=0.4)

            ax.set_xlabel("Days", fontsize=10)
            ax.set_ylabel("Percentage", fontsize=10)
            ax.set_title("Uptime and Downtime Report - Weekly", fontsize=12)
            ax.legend(fontsize=10)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.yticks(fontsize=8)

            sns.despine(left=True, bottom=True)

            plt.tight_layout()

            return fig


        ############################################################# Month Section ###############################################################
        def create_output_folder(folder_name):
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)


        def separate_csv_by_month(input_file, output_folder):
            data = pd.read_csv(input_file, parse_dates=['Days'], dayfirst=True, infer_datetime_format=False)

            data['Days'] = pd.to_datetime(data['Days'], format="%Y-%m-%d")

            print(data['Days'].dtype)
            print(data['Days'].head())

            grouped_data = data.groupby(data['Days'].dt.month)    
            for month, month_data in grouped_data:
                year = datetime.now().strftime("%Y")
                output_file = os.path.join(output_folder, f'month_{month:02d}_{year}.csv')
                month_data.to_csv(output_file, index=False)

        def calculate_avg_values(input_folder, output_folder):
            all_data = []
            for filename in os.listdir(input_folder):
                if filename.startswith("month_") and filename.endswith(".csv"):
                    file_path = os.path.join(input_folder, filename)
                    month_data = pd.read_csv(file_path)

                    avg_uptime = month_data["Uptime%"].mean()
                    avg_downtime = month_data["Downtime%"].mean()

                    filename_parts = filename.split("_")[1].split(".")[0].split("-")
                    if len(filename_parts) == 2:
                        month, year = filename_parts
                        month = int(month)
                        year = int(year)
                    else:
                        month = int(filename_parts[0])
                        year = datetime.now().year 

                    all_data.append({"Duration": f"{month}-{year}", "Up_Avg": avg_uptime, "Down_Avg": avg_downtime})

            avg_df = pd.DataFrame(all_data)

            avg_output_csv = os.path.join(output_folder, "average_values.csv")
            avg_df.to_csv(avg_output_csv, index=False)

        def create_bar_chart_m(averages_df):
            sns.set_style("darkgrid")
            custom_colors = ["#8B0000", "#00CED1"]
            sns.set_palette(custom_colors)

            fig, ax = plt.subplots(figsize=(8, 4))

            averages_df = averages_df.sort_values("Duration")

            dates = averages_df["Duration"]
            up_avg_values = averages_df["Up_Avg"]
            down_avg_values = averages_df["Down_Avg"]

            ax.bar(dates, down_avg_values, label="Downtime%", alpha=0.7, width=0.4)
            ax.bar(dates, up_avg_values, bottom=down_avg_values, label="Uptime%", alpha=0.7, width=0.4)

            ax.set_xlabel("Duration", fontsize=10)
            ax.set_ylabel("Percentage", fontsize=10)
            ax.set_title("Uptime and Downtime Report - Monthly", fontsize=12)
            ax.legend(fontsize=10)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.yticks(fontsize=8)

            sns.despine(left=True, bottom=True)

            plt.tight_layout()

            return fig

        def main():
            col1, col2 = st.columns([2, 3.5]) 
            search_text = col1.text_input("Enter search text:")
            col1.title("Settings")
            with col1:
                selected_date = st.date_input("Select Start Date", key="Date7")

                initial_time = datetime.strptime("00:00:00", "%H:%M:%S").time()

                col3, col4, col5 = col1.columns(3)
                selected_hour = col3.number_input("Hours", min_value=0, max_value=23, value=initial_time.hour, key="3")
                selected_minute = col4.number_input("Minutes", min_value=0, max_value=59, value=initial_time.minute, key="minute4")
                selected_second = col5.number_input("Seconds", min_value=0, max_value=59, value=initial_time.second, key="second4")

                time_value1 = datetime.combine(selected_date, time(selected_hour, selected_minute, selected_second))



                selected_date2 = st.date_input("Select End Date", key="Date8")

                col6, col7, col8 = col1.columns(3)
                selected_hour2 = col6.number_input("Hours", min_value=0, max_value=23, value=initial_time.hour, key="hour4")
                selected_minute2 = col7.number_input("Minutes", min_value=0, max_value=59, value=initial_time.minute, key="minute5")
                selected_second2 = col8.number_input("Seconds", min_value=0, max_value=59, value=initial_time.second, key="second5")

                time_value2 = datetime.combine(selected_date2, time(selected_hour2, selected_minute2, selected_second2))
            if col1.button("Enter"):
                zabbix_url = "https://18.191.78.153/api_jsonrpc.php"
                zabbix_user = "Zabbix"
                zabbix_password = "Paramaah@@123"
                subprocess.run("find /home/ubuntu/data/ -type f ! -name '1_aishanlogo.pdf' -exec rm -f {} \;", shell=True)
                results = search_zabbix_hostnames(search_text, zabbix_url, zabbix_user, zabbix_password)

            # download_graphs(search_text, zabbix_url, zabbix_user, zabbix_password, time_value1, time_value2,col2)

                output_file = "zabbix_hostnames_2.csv"
                with open(output_file, "w", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Hostname"])
                    writer.writerows([[hostname] for hostname in results])

                hostnames = []

                with open(output_file, "r") as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader) 
                    for row in reader:
                        hostnames.append(row[0])

                for hostname in hostnames:
                    if "WA" in hostname:
                        start_timestamp = int(time_value1.timestamp())
                        end_timestamp = int(time_value2.timestamp())
                        duration_in_seconds = end_timestamp - start_timestamp

                        duration_in_days = duration_in_seconds / 86400

                        conn = psycopg2.connect(database="zabbix_db1", user="zabbixuser", password="zabbixpass", host="18.222.141.167", port="5432")
                        cursor = conn.cursor()

                        query = """
                            SELECT DISTINCT
                                problem.objectid,
                                TO_CHAR(TO_TIMESTAMP(problem.clock), 'YYYY-MM-DD HH24:MI:SS') AS start_time,
                                triggers.description AS problem_description,
                                r.eventid AS r_eventid,
                                TO_CHAR(TO_TIMESTAMP(COALESCE(r.clock, EXTRACT(EPOCH FROM NOW()))), 'YYYY-MM-DD HH24:MI:SS') AS end_time,
                                CASE
                                    WHEN r.clock IS NOT NULL
                                        THEN (EXTRACT(EPOCH FROM TO_TIMESTAMP(r.clock)) - EXTRACT(EPOCH FROM TO_TIMESTAMP(problem.clock)))
                                    ELSE NULL
                                END AS duration,
                                hosts.host AS hostname
                            FROM
                                events problem
                                JOIN triggers ON triggers.triggerid = problem.objectid
                                LEFT JOIN events r ON r.objectid = problem.objectid AND r.value = 0 AND r.clock > problem.clock
                                    AND NOT EXISTS (
                                        SELECT 1 FROM events r2
                                        WHERE r2.objectid = r.objectid AND r2.value = 0 AND r2.clock > problem.clock AND r2.clock < r.clock
                                    )
                                LEFT JOIN functions f ON triggers.triggerid = f.triggerid
                                LEFT JOIN items i ON f.itemid = i.itemid
                                LEFT JOIN hosts ON i.hostid = hosts.hostid
                            WHERE
                                problem.object = 0
                                AND problem.clock >= %s
                                AND problem.clock <= %s
                                AND problem.value = 1
                        """
                        if hostname:
                            query += f"AND hosts.host = '{hostname}' "
                        query += "AND i.key_ = 'icmpping'"

                        cursor.execute(query,(start_timestamp, end_timestamp,))

                        rows = cursor.fetchall()

                        cursor.close()
                        conn.close()

                        ist = timezone('Asia/Kolkata')
                        converted_rows = []
                        for row in rows:
                            converted_start_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')).astimezone(ist)
                            converted_end_time = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')).astimezone(ist)
                            converted_row = (row[0], converted_start_time.strftime('%Y-%m-%d %H:%M:%S'), row[2], row[3], converted_end_time.strftime('%Y-%m-%d %H:%M:%S'), row[5], row[6])
                            converted_rows.append(converted_row)

                        downtime_per_day = {}
                        for row in converted_rows:
                            start_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S') 
                            end_time = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S')  

                            start_date = start_time.date()
                            end_date = end_time.date() 

                            if start_date == end_date:
                                duration = (end_time - start_time).total_seconds() 
                                downtime_per_day[start_date] = downtime_per_day.get(start_date, 0) + duration
                            else:
                                next_day_start = datetime.combine(start_date + timedelta(days=1), datetime.min.time())
                                duration = (next_day_start - start_time).total_seconds() 
                                downtime_per_day[start_date] = downtime_per_day.get(start_date, 0) + duration

                                intermediate_date = start_date + timedelta(days=1)
                                while intermediate_date != end_date:
                                    next_day_start = datetime.combine(intermediate_date + timedelta(days=1), datetime.min.time())
                                    duration = (next_day_start - datetime.combine(intermediate_date, datetime.min.time())).total_seconds()  
                                    downtime_per_day[intermediate_date] = downtime_per_day.get(intermediate_date, 0) + duration
                                    intermediate_date += timedelta(days=1)

                                duration = (end_time - datetime.combine(end_date, datetime.min.time())).total_seconds() 
                                downtime_per_day[end_date] = downtime_per_day.get(end_date, 0) + duration

                        start_date = time_value1.date() 
                        end_date = time_value2.date()

                        csv_data = []
                        current_date = start_date
                        downtime_percentages = []
                        uptime_percentages = []
                        while current_date <= end_date:
                            downtime = downtime_per_day.get(current_date, 0)
                            downtime_value = int(downtime)
                            downtime_percentage = (downtime / (24 * 60 * 60)) * 100 
                            uptime_percentage = 100 - downtime_percentage 

                            csv_data.append([current_date, downtime_percentage, uptime_percentage])
                            downtime_percentages.append(downtime_percentage)
                            uptime_percentages.append(uptime_percentage)
                            current_date += timedelta(days=1)
                        total_downtime_percentage = sum(downtime_percentages) / len(downtime_percentages)
                        total_uptime_percentage = sum(uptime_percentages) / len(uptime_percentages)
                        avg_downtime_percentage = sum(downtime_percentages) / len(downtime_percentages)
                        avg_uptime_percentage = 100 - avg_downtime_percentage
                        csv_filename = f"downtime_report_{hostname}.csv"
                        with open(csv_filename, mode="w", newline="") as file:
                            writer = csv.writer(file)
                            writer.writerow(["Days", "Downtime%", "Uptime%"]) 
                            writer.writerows(csv_data)
                            # Add a button for downloading the CSV file
                        # Convert the list of dictionaries to a DataFrame
                        csv_df = pd.DataFrame(csv_data)

                        # Convert the DataFrame to a CSV-formatted string
                        csv_string = csv_df.to_csv(index=False)

                        # Provide option to download the CSV file for the current host
                        csv_filename = f"downtime_report_{hostname}.csv"
                        b64 = base64.b64encode(csv_string.encode()).decode()
                        href = f'<a href="data:text/csv;charset=utf-8;base64,{b64}" download="{csv_filename}">Download CSV ({hostname})</a>'
                        st.markdown(f"Download the CSV file: {href}", unsafe_allow_html=True)
                        with col2:
                            if duration_in_days <= 31:
                                csv_data = read_csv_data(csv_filename)

                                column_names = ["Days", "Downtime%", "Uptime%"]
                                df = pd.DataFrame(csv_data[1:], columns=column_names)
                                st.dataframe(df,height=400,width=1200)

                                st.write(f"Average Downtime: {avg_downtime_percentage:.2f}%")
                                st.write(f"Average Uptime: {avg_uptime_percentage:.2f}%")

                                df = pd.read_csv(csv_filename)

                                dates = df["Days"]
                                downtime_percentages = df["Downtime%"]
                                uptime_percentages = df["Uptime%"]

                                sns.set_style("darkgrid")
                                custom_colors = ["#8B0000", "#00CED1"]
                                sns.set_palette(custom_colors)

                                fig, ax = plt.subplots(figsize=(8, 4))

                                ax.bar(dates, downtime_percentages, label="Downtime%", alpha=0.7, width=0.4)
                                ax.bar(dates, uptime_percentages, bottom=downtime_percentages, label="Uptime%", alpha=0.7, width=0.4)
                                ax.set_xlabel("Days", fontsize=10)
                                ax.set_ylabel("Percentage", fontsize=10)
                                ax.set_title("Uptime and Downtime Report - Daily", fontsize=12)
                                ax.legend(fontsize=10)
                                plt.xticks(rotation=45, ha='right', fontsize=8)
                                plt.yticks(fontsize=8)

                                sns.despine(left=True, bottom=True)

                                plt.tight_layout()
                                plt.show()
                                st.pyplot(fig)

                                pdf_content_bar = convert_graph_to_pdf(fig,hostname)

                                pdf_filename_bar = f"bar_graph_{hostname}.pdf"
                                b64_pdf = base64.b64encode(pdf_content_bar).decode()
                                href_pdf = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename_bar}" class="button"><i class="fas fa-download" style="color: black;"></i> Bar_Chart PDF</a>'


                                st.markdown(f"{href_pdf}", unsafe_allow_html=True)

                                csv_filepath = os.path.join(".", csv_filename)

                                pdf_filename = f"1_downtime_report_{search_text}_{hostname}.pdf"
                                pdf_filepath = os.path.join("/home/ubuntu/data", pdf_filename)
                                convert_csv_to_pdf(csv_filepath, pdf_filepath, avg_uptime_percentage, avg_downtime_percentage, hostname)

                                with open(pdf_filepath, "rb") as pdf_file:
                                    pdf_content = pdf_file.read()
                                    b64_pdf = base64.b64encode(pdf_content).decode("utf-8")
                                    download_pdf_button_html = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" class="button"><i class="fas fa-download" style="color: black;"></i> Up_Down PDF</a>'
                                    st.markdown(download_pdf_button_html, unsafe_allow_html=True)
                            elif 31 < duration_in_days < 182:
                                duration_in_weeks = duration_in_days / 7
                                averages_df = group_into_weekly_csv(csv_filename)

                                csv_data = read_csv_data_m("/home/ubuntu/weekly_sorted/weekly_averages.csv")



                                column_names = ["Days", "Uptime%", "Downtime%"]
                                df = pd.DataFrame(csv_data, columns=column_names)
                                st.dataframe(df,height=400,width=800)


                                fig = create_bar_chart(averages_df)
                                st.pyplot(fig)
                                pdf_bytes = convert_graph_to_pdf(fig, hostname)
                                st.download_button(
                                    label="Download as PDF",
                                    data=pdf_bytes,
                                    file_name=f"bar_graph_{hostname}.pdf",
                                    mime="application/pdf"
                                )
                                csv_filepath = os.path.join(".", csv_filename)

                                pdf_filename = f"1_downtime_report_{search_text}_{hostname}.pdf"
                                pdf_filepath = os.path.join("/home/ubuntu/data", pdf_filename)
                                convert_csv_to_pdf(csv_filepath, pdf_filepath, avg_uptime_percentage, avg_downtime_percentage,hostname)

                                with open(pdf_filepath, "rb") as pdf_file:
                                    pdf_content = pdf_file.read()
                                    b64_pdf = base64.b64encode(pdf_content).decode("utf-8")
                                    download_pdf_button_html = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" class="button"><i class="fas fa-download" style="color: black;"></i> Up_Down PDF</a>'
                                    st.markdown(download_pdf_button_html, unsafe_allow_html=True)

                            else:
                                input_csv_file = csv_filename
                                output_folder_name = "output_files"

                                create_output_folder(output_folder_name)
                                separate_csv_by_month(input_csv_file, output_folder_name)
                                calculate_avg_values(output_folder_name, output_folder_name)

                                averages_df = pd.read_csv(os.path.join(output_folder_name, "average_values.csv"))
                                csv_data = read_csv_data_m("/home/ubuntu/output_files/average_values.csv")



                                column_names = ["Days", "Uptime%", "Downtime%"]
                                df = pd.DataFrame(csv_data, columns=column_names)
                                st.dataframe(df,height=400,width=800)


                                fig = create_bar_chart_m(averages_df)
                                st.pyplot(fig)

                                pdf_bytes = convert_graph_to_pdf(fig, hostname)
                                st.download_button(
                                    label="Download Bar Chart as PDF",
                                    data=pdf_bytes,
                                    file_name="bar_chart.pdf",
                                    mime="application/pdf"
                                )
                                csv_filepath = os.path.join(".", csv_filename)
                                pdf_filename = f"1_downtime_report_{search_text}_{hostname}.pdf"
                                pdf_filepath = os.path.join("/home/ubuntu/data", pdf_filename)
                                convert_csv_to_pdf(csv_filepath, pdf_filepath, avg_uptime_percentage, avg_downtime_percentage,hostname)

                                with open(pdf_filepath, "rb") as pdf_file:
                                    pdf_content = pdf_file.read()
                                    b64_pdf = base64.b64encode(pdf_content).decode("utf-8")
                                    download_pdf_button_html = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" class="button"><i class="fas fa-download" style="color: black;"></i> Up_Down PDF</a>'
                                    st.markdown(download_pdf_button_html, unsafe_allow_html=True)

            st.markdown("PDF files to combine:")
            folder_path = "/home/ubuntu/data"

            if st.button("Combine",key="7"):
                if not folder_path:
                    st.warning("Please enter the folder path.")
                else:
                    pdf_files = get_pdf_files_from_folder(folder_path)
                    if not pdf_files:
                        st.warning("No PDF files found in the specified folder.")
                    else:
                        merged_pdf = combine_pdfs_with_watermark(pdf_files)
                        st.success("PDF files combined successfully! You can download the combined PDF below.")
                        st.download_button("Download Combined PDF", data=merged_pdf, file_name="combined_pdf.pdf", mime="application/pdf")

        if __name__ == "__main__":
            st.markdown('<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" rel="stylesheet">', unsafe_allow_html=True)


            st.markdown(
                """
                <style>
                .button {
                    display: inline-block;
                    margin-right: 10px;
                    padding: 8px 16px;
                    border: none;
                    background-color: #E5E4E2;
                    color: black;
                    cursor: pointer;
                    transition: background-color 0.3s, transform 0.3s, box-shadow 0.3s;
                    text-decoration: none;
                    border-radius: 4px;
                    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
                }
                .button:hover {
                    background-color: #D1D0CE;
                    box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
                }
                .button:active {
                    transform: translateY(2px);
                    box-shadow: 0px 0px 2px rgba(0, 0, 0, 0.2);
                }
                .button i {
                    margin-right: 5px;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            main()

    if menu_id == "Graph":
        
            # Date and time selection
        def read_graph_id_from_csv(csv_file):
            # Function to read the graph ID from the CSV file
            with open(csv_file, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get("Graph ID"):
                        return row["Graph ID"]
            return None

        def create_graph_csv(selected_graphname):

            if selected_graphname != ' - ':
                # Display selected data
                print('Selected Hostgroup:', selected_hostgroup)
                print('Selected Hostname:', selected_hostname)
                print('Selected Graphname:', selected_graphname)
                # Optionally, you can display the details of the selected graphname
                selected_graph_data = final_data[final_data['Graph Name'] == selected_graphname]
                if not selected_graph_data.empty:
                    graph_id = selected_graph_data.iloc[0]['Graph ID']
                    st.dataframe(selected_graph_data, width=2000)
                    # Save the graph ID to a CSV file
                    graph_ids = pd.DataFrame({'Graph ID': [graph_id]})
                    graph_ids.to_csv('graph_ids.csv', index=False)
        selected2 = option_menu(None, ["Calendar", "Time pre-defined"],
            icons=['house', 'cloud-upload'],
            menu_icon="cast", default_index=0, orientation="horizontal")
        st.markdown('<hr style="margin-left: 0.5cm; margin-right: 0.5cm; border-top: 3px double black; margin-top: 0.5rem; margin-bottom: 0.5rem;">', unsafe_allow_html=True)

        if selected2 == "Calendar" :
 
            data = pd.read_csv('zabbix_graphs.csv')

            # Get unique hostgroup names
            hostgroups = data['Host Group Names'].unique()


            col1, col2 = st.columns([1, 2.5]) 

            with col1 :
                selected_hostgroup = st.selectbox('Select Hostgroup', [' - '] + list(hostgroups),key="hg2")

                # Filter data based on selected hostgroup
                filtered_data = data[data['Host Group Names'] == selected_hostgroup] if selected_hostgroup != ' - ' else data

                # Get unique hostnames within the selected hostgroup
                hostnames = filtered_data['Hostname'].unique()

                # Hostname selectbox
                selected_hostname = st.selectbox('Select Hostname', [' - '] + list(hostnames),key="hn1")

                # Filter data based on selected hostname
                final_data = filtered_data[filtered_data['Hostname'] == selected_hostname] if selected_hostname != ' - ' else filtered_data

                # Get unique graph names for the selected hostname
                graph_names = final_data['Graph Name'].unique()

                # Graphname selectbox
                selected_graphname = st.selectbox('Select Graphname', [' - '] + list(graph_names),key="gr1")
                create_graph_csv(selected_graphname)
                # Input fields in the sidebar
                csv_file = "graph_ids.csv"

                selected_date = st.date_input("Select Date",key="Date9")

                # Set the initial time to 00:00:00
                initial_time = datetime.strptime("00:00:00", "%H:%M:%S").time()

                # Set the initial time to the current time
                current_time = datetime.now().time()

                # Create separate input boxes for hours, minutes, and seconds for the first time_value input
                col3, col4, col5 = st.columns(3)
                selected_hour = col3.number_input("", min_value=0, max_value=23, value=initial_time.hour, key="4")
                selected_minute = col4.number_input("", min_value=0, max_value=59, value=initial_time.minute, key="minute6")
                selected_second = col5.number_input("", min_value=0, max_value=59, value=initial_time.second, key="second6")

                # Combine the selected date and time for the first time_value input
                time_value = datetime.combine(selected_date, time(selected_hour, selected_minute, selected_second))

                selected_date2 = st.date_input("Select Date",key="Date10")

                # Create separate input boxes for hours, minutes, and seconds for the second time_value input
                col6, col7, col8 = st.columns(3)
                selected_hour2 = col6.number_input("", min_value=0, max_value=23, value=current_time.hour, key="hour5")
                selected_minute2 = col7.number_input("", min_value=0, max_value=59, value=current_time.minute, key="minute7")
                selected_second2 = col8.number_input("", min_value=0, max_value=59, value=current_time.second, key="second7")

                # Combine the selected date and time for the second time_value input
                time_value2 = datetime.combine(selected_date2, time(selected_hour2, selected_minute2, selected_second2))

            # Download button
            if col1.button("Download Graph"):
                # Read the graph ID from the CSV file
                graph_id = read_graph_id_from_csv(csv_file)

                # Check if graph ID is found in the CSV file
                if graph_id is None:
                    st.warning("Graph ID not found in the CSV file.")
                # Generate a unique filename with timestamp
                filename = f"graph_{graph_id}.png"

                bash_cmd = f"./ishan.sh {graph_id} \"{time_value}\" \"{time_value2}\" {filename}"
                subprocess.run(bash_cmd, shell=True, capture_output=True)

                with col2 :
                    # Display the downloaded graph
                    st.success("Graph downloaded successfully!")
                    graph_content = open(filename, "rb").read()
                    st.image(graph_content, caption="Downloaded Graph", use_column_width=True)


                    with open(filename, "rb") as file:
                        btn = st.download_button(
                                label="Download image",
                                data=file,
                                file_name=filename,
                                mime="image/png"
                            )
                    def convert_image_to_pdf(image_path, output_path):
                        try:
                            image = Image.open(image_path)
                            image.save(output_path, "PDF", resolution=100.0)
                            print("Image converted to PDF successfully!")
                        except Exception as e:
                            print("An error occurred:", str(e))

                    # Example usage
                    image_path = filename  # Replace with the path to your image file
                    output_path = "sample.pdf"  # Replace with the desired output path

                    convert_image_to_pdf(image_path, output_path)


        if selected2 == "Time pre-defined" :

            data = pd.read_csv('zabbix_graphs.csv')

            # Get unique hostgroup names
            hostgroups = data['Host Group Names'].unique()


            col1, col2 = st.columns([1, 2.5]) 

            with col1 :
                selected_hostgroup = st.selectbox('Select Hostgroup', [' - '] + list(hostgroups),key="hg3")

                # Filter data based on selected hostgroup
                filtered_data = data[data['Host Group Names'] == selected_hostgroup] if selected_hostgroup != ' - ' else data

                # Get unique hostnames within the selected hostgroup
                hostnames = filtered_data['Hostname'].unique()

                # Hostname selectbox
                selected_hostname = st.selectbox('Select Hostname', [' - '] + list(hostnames),key="hn3")

                # Filter data based on selected hostname
                final_data = filtered_data[filtered_data['Hostname'] == selected_hostname] if selected_hostname != ' - ' else filtered_data

                # Get unique graph names for the selected hostname
                graph_names = final_data['Graph Name'].unique()

                # Graphname selectbox
                selected_graphname = st.selectbox('Select Graphname', [' - '] + list(graph_names),key="gr2")
                create_graph_csv(selected_graphname)
                # Input fields in the sidebar
                csv_file = "graph_ids.csv"
                import math

                # Get the current date and time
                current_time = datetime.now()

                # Predefined time filters
                time_filters = {
                    "Last 2 days": 2 * 24 * 60 * 60,
                    "Last 7 days": 7 * 24 * 60 * 60,
                    "Last 30 days": 30 * 24 * 60 * 60,
                    "Last 3 months": 3 * 30 * 24 * 60 * 60,
                    "Last 6 months": 6 * 30 * 24 * 60 * 60,
                    "Last 1 year": 365 * 24 * 60 * 60,
                    "Last 2 years": 2 * 365 * 24 * 60 * 60,
                    "Yesterday": 24 * 60 * 60,
                    "Day before yesterday": 2 * 24 * 60 * 60,
                    "This day last week": 7 * 24 * 60 * 60,
                    "Previous week": 7 * 24 * 60 * 60,
                    "Previous month": 30 * 24 * 60 * 60,
                    "Previous year": 365 * 24 * 60 * 60,
                    "Today": 0,
                    "Today so far": 0,  # TODO: Calculate the value based on current time
                    "This week": 0,  # TODO: Calculate the value based on current time
                    "This week so far": 0,  # TODO: Calculate the value based on current time
                    "This month": 0,  # TODO: Calculate the value based on current time
                    "This month so far": 0,  # TODO: Calculate the value based on current time
                    "This year": 0,  # TODO: Calculate the value based on current time
                    "This year so far": 0,  # TODO: Calculate the value based on current time
                    "Last 5 minutes": 5 * 60,
                    "Last 15 minutes": 15 * 60,
                    "Last 30 minutes": 30 * 60,
                    "Last 1 hour": 60 * 60,
                    "Last 3 hours": 3 * 60 * 60,
                    "Last 6 hours": 6 * 60 * 60,
                    "Last 12 hours": 12 * 60 * 60,
                    "Last 1 day": 24 * 60 * 60
                }

                # Dropdown to select the time filter
                selected_time_filter = st.selectbox("Select Time Filter", list(time_filters.keys()),key="tf")

                # Convert the selected time filter into seconds
                time_filter_value = time_filters[selected_time_filter]

                st.write("Selected Time Value (Seconds):", time_filter_value)
                    # Download button
                if st.button("Download Graph",key="8"):
                    # Read the graph ID from the CSV file
                    graph_id = read_graph_id_from_csv(csv_file)

                    # Check if graph ID is found in the CSV file
                    if graph_id is None:
                        st.warning("Graph ID not found in the CSV file.")
                    # Generate a unique filename with timestamp
                    filename = f"graph_{graph_id}.png"
                    st.write("Selected Time Value:", time_filter_value)


                    bash_cmd = f"./ishan2.sh {graph_id} {time_filter_value} {filename}"
                    subprocess.run(bash_cmd, shell=True, capture_output=True)

                    # Display the downloaded graph
                    st.success("Graph downloaded successfully!")
                    graph_content = open(filename, "rb").read()
                    st.image(graph_content, caption="Downloaded Graph", use_column_width=True)
                    
                    with open(filename, "rb") as file:
                        btn = st.download_button(
                                label="Download image",
                                data=file,
                                file_name=filename,
                                mime="image/png"
                            )
                    def convert_image_to_pdf(image_path, output_path):
                        try:
                            image = Image.open(image_path)
                            image.save(output_path, "PDF", resolution=100.0)
                            print("Image converted to PDF successfully!")
                        except Exception as e:
                            print("An error occurred:", str(e))

                    # Example usage
                    image_path = filename  # Replace with the path to your image file
                    output_path = "sample.pdf"  # Replace with the desired output path

                    convert_image_to_pdf(image_path, output_path)          


    if menu_id == "Logout":
            authenticator.logout("Logout")
    
    if menu_id == "Config":

        selected2 = option_menu(None, ["Reset Password", "Update_User Details", "New User"],
            icons=['house', 'cloud-upload'],
            menu_icon="cast", default_index=0, orientation="horizontal")

        if selected2 == "Reset Password" :
            try:
                if authenticator.reset_password(st.session_state["username"], 'Reset password'):
                    st.success('Password modified successfully')
                    with open('config.yaml', 'w') as file:
                        yaml.dump(config, file, default_flow_style=False)
                    # Random password should be transferred to the user securely
            except Exception as e:
                st.error(e)

        if selected2 == "Update_User Details":
            try:
                if authenticator.update_user_details(st.session_state["username"], 'Update user details'):
                    st.success('Entries updated successfully')
                    with open('config.yaml', 'w') as file:
                        yaml.dump(config, file, default_flow_style=False)
            except Exception as e:
                st.error(e)
        if selected2 == "New User":
            try:
                if authenticator.register_user('Register user', preauthorization=False):
                    st.success('User registered successfully')
                    with open('config.yaml', 'w') as file:
                        yaml.dump(config, file, default_flow_style=False)
            except Exception as e:
                st.error(e)

    if menu_id == "Info":
        import streamlit as st
        import yaml

        # Load the YAML configuration file
        with open('config.yaml', 'r') as config_file:
            config_data = yaml.load(config_file, Loader=yaml.FullLoader)

        # Create a Streamlit app
        st.title("User Login")

        # Input field for name (prepopulated with session state value)
        st.write('<style>div.Widget.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        name = st.text_input("Name:", value=st.session_state.get("name", ""))

        # Checkbox to toggle password visibility
        show_password = st.checkbox("Show Password")

        # Function to retrieve the password based on the name
        def get_password(name):
            for username, user_data in config_data.get("credentials", {}).get("usernames", {}).items():
                if user_data.get("name") == name:
                    return user_data.get("password")
            return None
        def get_email(name):
            for username, user_data in config_data.get("credentials", {}).get("usernames", {}).items():
                if user_data.get("name") == name:
                    return user_data.get("email")
            return None
        # Display the password when "Show Password" is checked
        if show_password:
            password = get_password(name)
            if password:
                st.write(f"Password for {name}: {password}")  # Display plaintext password
            else:
                st.write(f"No password found for {name}")
        else:
            st.write("Password: ********")  # Display asterisks to hide the password
        email = get_email(name)
        st.text_input("Email ID:", value=email)

    if menu_id == "UI Server":
        import time  # to simulate a real time data, time loop
        import numpy as np  # np mean, np random
        import pandas as pd  # read csv, df manipulation
        import plotly.express as px  # interactive charts
        import streamlit as st  # 🎈 data web app development
        # read csv from a github repo
        dataset_url = "https://raw.githubusercontent.com/Lexie88rus/bank-marketing-analysis/master/bank.csv"

        # read csv from a URL
        @st.cache_data
        def get_data() -> pd.DataFrame:
            return pd.read_csv(dataset_url)

        df = get_data()

        # dashboard title
        st.title("Real-Time / Live Data Science Dashboard")

        # top-level filters
        job_filter = st.selectbox("Select the Job", pd.unique(df["job"]))

        # creating a single-element container
        placeholder = st.empty()

        # dataframe filter
        df = df[df["job"] == job_filter]

        # near real-time / live feed simulation
        for seconds in range(200):

            df["age_new"] = df["age"] * np.random.choice(range(1, 5))
            df["balance_new"] = df["balance"] * np.random.choice(range(1, 5))

            # creating KPIs
            avg_age = np.mean(df["age_new"])

            count_married = int(
                df[(df["marital"] == "married")]["marital"].count()
                + np.random.choice(range(1, 30))
            )

            balance = np.mean(df["balance_new"])

            with placeholder.container():

                # create three columns
                kpi1, kpi2, kpi3 = st.columns(3)

                # fill in those three columns with respective metrics or KPIs
                kpi1.metric(
                    label="Age ⏳",
                    value=round(avg_age),
                    delta=round(avg_age) - 10,
                )
                
                kpi2.metric(
                    label="Married Count 💍",
                    value=int(count_married),
                    delta=-10 + count_married,
                )
                
                kpi3.metric(
                    label="A/C Balance ＄",
                    value=f"$ {round(balance,2)} ",
                    delta=-round(balance / count_married) * 100,
                )

                # create two columns for charts
                fig_col1, fig_col2 = st.columns(2)
                with fig_col1:
                    st.markdown("### First Chart")
                    fig = px.density_heatmap(
                        data_frame=df, y="age_new", x="marital"
                    )
                    st.write(fig)
                    
                with fig_col2:
                    st.markdown("### Second Chart")
                    fig2 = px.histogram(data_frame=df, x="age_new")
                    st.write(fig2)

                st.markdown("### Detailed Data View")
                st.dataframe(df)
                time.sleep(1)

elif st.session_state["authentication_status"] == False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] == None:
    st.warning('Please enter your username and password')
footer = """<style>
a:link , a:visited{
color: blue;
background-color: transparent;
}

a:hover,  a:active {
color: red;
background-color: #d3d3d3;
}

.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: white;
color: black;
text-align: center;
}
</style>
<div class="footer">
<p>Developed with <img src="https://avatars3.githubusercontent.com/u/45109972?s=400&v=4" width="25px" height="25px"> by <a href="https://www.paramaah.com" target="_blank">Paramaah</a></p>
</div>
"""
st.markdown(footer,unsafe_allow_html=True)