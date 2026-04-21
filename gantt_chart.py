import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

def create_gantt_chart(data):
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Calculate end dates
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = df['start_date'] + pd.to_timedelta(df['duration_days'], unit='D')
    
    # Create task labels combining task_name and location
    df['task_label'] = df['task_name'] + ' (' + df['location'] + ')'
    
    # Create Gantt chart
    fig = px.timeline(df, 
                     x_start='start_date', 
                     x_end='end_date', 
                     y='task_label', 
                     color='activity_type',
                     title='Gantt Chart of Mining Activities',
                     hover_data=['progress_meters', 'completed', 'drill_used'])
    
    # Update layout
    fig.update_yaxes(categoryorder='total ascending')
    fig.update_layout(
        xaxis_title='Timeline',
        yaxis_title='Tasks',
        showlegend=True,
        height=600,
        width=1000
    )
    
    # Show the chart
    fig.show()

if __name__ == "__main__":
    # Data
    data = [{'task_name': 'B4C Tunneling', 'start_date': '2025-04-01', 'duration_days': 30.0, 'location': 'B4C', 'progress_meters': 24.9, 'completed': False, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 1'}, {'task_name': 'CRM7-8 Tunneling', 'start_date': '2025-04-01', 'duration_days': 15.0, 'location': 'CRM7-8', 'progress_meters': 8.3, 'completed': True, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 2'}, {'task_name': 'RM8 Rm_blasting', 'start_date': '2025-04-01', 'duration_days': 30, 'location': 'RM8', 'progress_meters': 12.83, 'completed': False, 'activity_type': 'Rm_blasting', 'drill_used': 'Jackleg 2'}, {'task_name': 'RDAS Tunneling', 'start_date': '2025-04-16', 'duration_days': 15.0, 'location': 'RDAS', 'progress_meters': 12.45, 'completed': False, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 2'}, {'task_name': 'B4C Tunneling', 'start_date': '2025-05-01', 'duration_days': 20.5, 'location': 'B4C', 'progress_meters': 12.865, 'completed': True, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 2'}, {'task_name': 'RM8 Rm_blasting', 'start_date': '2025-05-01', 'duration_days': 31, 'location': 'RM8', 'progress_meters': 12.83, 'completed': False, 'activity_type': 'Rm_blasting', 'drill_used': 'Jackleg 2'}, {'task_name': 'RDAS Tunneling', 'start_date': '2025-05-01', 'duration_days': 31.0, 'location': 'RDAS', 'progress_meters': 25.73, 'completed': False, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 1'}, {'task_name': 'RC6C Tunneling', 'start_date': '2025-05-21', 'duration_days': 11, 'location': 'RC6C', 'progress_meters': 8.715, 'completed': False, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 2'}, {'task_name': 'RM8 Rm_blasting', 'start_date': '2025-06-01', 'duration_days': 3, 'location': 'RM8', 'progress_meters': 1.283, 'completed': True, 'activity_type': 'Rm_blasting', 'drill_used': 'Jackleg 2'}, {'task_name': 'RDAS Tunneling', 'start_date': '2025-06-01', 'duration_days': 30.0, 'location': 'RDAS', 'progress_meters': 24.9, 'completed': False, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 1'}, {'task_name': 'RC6C Tunneling', 'start_date': '2025-06-01', 'duration_days': 30.0, 'location': 'RC6C', 'progress_meters': 24.485, 'completed': False, 'activity_type': 'Tunneling', 'drill_used': 'Jackleg 2'}]
    
    # Call the function
    create_gantt_chart(data)