import boto3
import uuid
from decouple import config
from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from utilities import constants
from sendgrid import SendGridAPIClient
from django.conf import settings
from sendgrid.helpers.mail import Mail, Personalization, Email, Bcc
from python_http_client import exceptions
from django.core.mail import send_mail
import logging
logger = logging.getLogger("django")

def upload_to_s3(file, folder):
    if not folder:
        raise ValueError("Folder name is required")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=config("s3AccessKey"),
        aws_secret_access_key=config("s3Secret"),
        )
    
    file_extension = file.name.split(".")[-1]
    file_name = f"{folder}/{uuid.uuid4()}.{file_extension}"
    bucket = config("S3_BUCKET_NAME")

    s3.upload_fileobj(
        file,
        bucket,
        file_name,
        ExtraArgs={
            "ContentType": file.content_type,
            "ACL": "public-read"
        }

    )
    return f"https://{bucket}.s3.amazonaws.com/{file_name}"
    

class DynamicPDFGenerator:
    def __init__(self, data, title="Report", page_size=A4):
        """
        :param data: List of dicts. Keys will be used as column headers
        :param title: Title of the PDF
        :param page_size: Page size (A4, letter, etc)
        """
        self.data = data
        self.title = title
        self.page_size = page_size
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
    
    def _build_table_data(self):
        """
        Convert list of dicts to list of lists for Platypus Table
        """
        if not self.data:
            return [["No data available"]]
        
        # Dynamic columns from keys of the first dict
        headers = list(self.data[0].keys())
        table_data = [headers]
        
        for record in self.data:
            row = [str(record.get(col, "")) for col in headers]
            table_data.append(row)
        
        return table_data
    
    def _get_table_style(self):
        """
        Table styling
        """
        return TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#d3d3d3")),  # Header background
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.25, colors.black),
        ])
    
    def generate_pdf(self):
        """
        Generates PDF and returns Django HttpResponse
        """
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.page_size,
            rightMargin=30,
            leftMargin=30,
            topMargin=50,
            bottomMargin=30
        )

        elements = []

        # Title
        elements.append(Paragraph(self.title, self.styles['Title']))
        elements.append(Spacer(1, 12))

        # Table
        table_data = self._build_table_data()
        table = Table(table_data, repeatRows=1)
        table.setStyle(self._get_table_style())
        elements.append(table)

        doc.build(elements)
        self.buffer.seek(0)

        response = HttpResponse(self.buffer, content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="{self.title.replace(" ", "_")}.pdf"'
        return response

def send_pdf_view_link(email, pdf_url, user_name):
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=email,
        subject="Employee PDF Report",
        plain_text_content=f"""
        Dear {user_name},

        Your employee report has been generated successfully.

        You can view the report by clicking the link below:
        {pdf_url}

        If you did not request this report, please ignore this email.

        Best regards,
        Administration Team
        """
            )

    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    sg.send(message)