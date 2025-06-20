"""
PDF 생성 유틸리티 모듈 - 전문 보고서 스타일
"""
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.rl_config

# 경고 비활성화
reportlab.rl_config.warnOnMissingFontGlyphs = 0

# 폰트 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS_DIR = os.path.join(BASE_DIR, 'static', 'fonts', 'nanum')

try:
    pdfmetrics.registerFont(TTFont('NanumGothic', os.path.join(FONTS_DIR, 'NanumGothic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NanumGothicBold', os.path.join(FONTS_DIR, 'NanumGothic-Bold.ttf')))
    FONT_AVAILABLE = True
except:
    FONT_AVAILABLE = False

# 전문 색상 팔레트
PRIMARY_BLUE = colors.Color(0.067, 0.184, 0.243)      # #112E3E - 진한 네이비
ACCENT_ORANGE = colors.Color(1.0, 0.6, 0.0)           # #FF9900 - AWS 오렌지
LIGHT_BLUE = colors.Color(0.941, 0.969, 0.988)       # #F0F7FC - 연한 파랑
MEDIUM_GREY = colors.Color(0.5, 0.5, 0.5)            # #808080 - 중간 회색
LIGHT_GREY = colors.Color(0.95, 0.95, 0.95)          # #F2F2F2 - 연한 회색
DARK_GREY = colors.Color(0.2, 0.2, 0.2)              # #333333 - 진한 회색

# 상태 색상
STATUS_SUCCESS = colors.Color(0.133, 0.545, 0.133)   # #228B22 - 성공
STATUS_WARNING = colors.Color(1.0, 0.647, 0.0)       # #FFA500 - 경고
STATUS_DANGER = colors.Color(0.863, 0.078, 0.235)    # #DC143C - 위험

def get_font_name(bold=False):
    """사용 가능한 폰트 반환"""
    if FONT_AVAILABLE:
        return 'NanumGothicBold' if bold else 'NanumGothic'
    return 'Helvetica-Bold' if bold else 'Helvetica'

def get_status_info(status):
    """상태별 정보 반환"""
    status_map = {
        'ok': ('정상', STATUS_SUCCESS, '✓'),
        'pass': ('정상', STATUS_SUCCESS, '✓'),
        'warning': ('주의', STATUS_WARNING, '⚠'),
        'error': ('위험', STATUS_DANGER, '✗'),
        'fail': ('위험', STATUS_DANGER, '✗'),
        'unknown': ('알 수 없음', MEDIUM_GREY, '?')
    }
    return status_map.get(str(status).lower(), ('알 수 없음', MEDIUM_GREY, '?'))

class HeaderFooter:
    """헤더/푸터 클래스"""
    def __init__(self, title, subtitle=""):
        self.title = title
        self.subtitle = subtitle
    
    def header(self, canvas, doc):
        canvas.saveState()
        # 헤더 배경
        canvas.setFillColor(PRIMARY_BLUE)
        canvas.rect(0, A4[1] - 60, A4[0], 60, fill=1)
        
        # AWS 로고 영역 (오렌지 박스)
        canvas.setFillColor(ACCENT_ORANGE)
        canvas.rect(20, A4[1] - 50, 40, 30, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont(get_font_name(True), 12)
        canvas.drawString(25, A4[1] - 40, "AWS")
        
        # 제목
        canvas.setFillColor(colors.white)
        canvas.setFont(get_font_name(True), 16)
        canvas.drawString(80, A4[1] - 35, self.title)
        
        if self.subtitle:
            canvas.setFont(get_font_name(), 10)
            canvas.drawString(80, A4[1] - 50, self.subtitle)
        
        canvas.restoreState()
    
    def footer(self, canvas, doc):
        canvas.saveState()
        # 푸터 라인
        canvas.setStrokeColor(LIGHT_GREY)
        canvas.setLineWidth(1)
        canvas.line(20, 40, A4[0] - 20, 40)
        
        # 페이지 번호
        canvas.setFillColor(MEDIUM_GREY)
        canvas.setFont(get_font_name(), 9)
        page_text = f"페이지 {doc.page}"
        canvas.drawRightString(A4[0] - 20, 25, page_text)
        
        # 생성 정보
        canvas.drawString(20, 25, f"생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}")
        
        canvas.restoreState()

class SectionDivider(Flowable):
    """섹션 구분선"""
    def __init__(self, width, color=ACCENT_ORANGE, thickness=2):
        Flowable.__init__(self)
        self.width = width
        self.color = color
        self.thickness = thickness
    
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

def create_info_box(title, content, width, bg_color=LIGHT_BLUE):
    """정보 박스 생성 (Paragraph 기반)"""
    # 제목 스타일
    title_style = ParagraphStyle(
        name='BoxTitle',
        fontName=get_font_name(True),
        fontSize=12,
        leading=16,
        textColor=colors.white,
        alignment=0,
        leftIndent=15,
        rightIndent=15,
        spaceBefore=10,
        spaceAfter=10
    )
    
    # 내용 스타일
    content_style = ParagraphStyle(
        name='BoxContent',
        fontName=get_font_name(),
        fontSize=10,
        leading=14,
        textColor=DARK_GREY,
        alignment=0,
        leftIndent=15,
        rightIndent=15,
        spaceBefore=15,
        spaceAfter=15
    )
    
    # 제목과 내용을 테이블로 구성 (배경색 적용을 위해)
    data = [[Paragraph(title, title_style)], [Paragraph(content, content_style)]]
    table = Table(data, colWidths=[width])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('BACKGROUND', (0, 1), (-1, 1), bg_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM_GREY)
    ]))
    
    return table

def generate_check_result_pdf(check_result, service_name, check_id, check_info, username, timestamp):
    """전문 보고서 스타일 PDF 생성"""
    
    # 시간 포맷팅
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime('%Y년 %m월 %d일 %H시 %M분')
        except:
            formatted_time = str(timestamp)
    else:
        formatted_time = timestamp.strftime('%Y년 %m월 %d일 %H시 %M분')
    
    buffer = io.BytesIO()
    
    # 문서 설정
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25*mm,
        rightMargin=25*mm,
        topMargin=80,  # 헤더 공간
        bottomMargin=60  # 푸터 공간
    )
    
    page_width = A4[0] - 50*mm
    
    # 헤더/푸터 설정
    header_footer = HeaderFooter("AWS 서비스 분석 보고서", "Service Advisor Report")
    
    # 스타일 정의
    title_style = ParagraphStyle(
        name='ReportTitle',
        fontName=get_font_name(True),
        fontSize=20,
        leading=24,
        textColor=PRIMARY_BLUE,
        spaceAfter=20,
        alignment=1  # 중앙 정렬
    )
    
    section_title_style = ParagraphStyle(
        name='SectionTitle',
        fontName=get_font_name(True),
        fontSize=14,
        leading=18,
        textColor=PRIMARY_BLUE,
        spaceBefore=20,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        name='Body',
        fontName=get_font_name(),
        fontSize=11,
        leading=16,
        textColor=DARK_GREY,
        spaceAfter=8
    )
    
    # 문서 내용
    elements = []
    
    # 메인 제목
    elements.append(Paragraph(f"{service_name.upper()} 서비스 분석 보고서", title_style))
    elements.append(SectionDivider(page_width))
    elements.append(Spacer(1, 20))
    
    # 검사 개요 섹션
    elements.append(Paragraph("1. 검사 개요", section_title_style))
    
    # 기본 정보 테이블
    basic_info = [
        ["검사 항목", check_info.get('name', check_id)],
        ["검사 ID", check_id],
        ["대상 서비스", service_name.upper()],
        ["검사 실행자", username],
        ["검사 일시", formatted_time]
    ]
    
    basic_table = Table(basic_info, colWidths=[page_width*0.25, page_width*0.75])
    basic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GREY),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('FONTNAME', (0, 0), (0, -1), get_font_name(True)),
        ('FONTNAME', (1, 0), (1, -1), get_font_name()),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GREY)
    ]))
    
    elements.append(basic_table)
    elements.append(Spacer(1, 20))
    
    # 검사 결과 섹션
    elements.append(Paragraph("2. 검사 결과", section_title_style))
    
    # 상태 정보
    status_text, status_color, status_icon = get_status_info(check_result.get('status', 'unknown'))
    
    # 결과 요약 박스
    result_summary = f"""
    <b>검사 상태:</b> {status_icon} {status_text}<br/>
    <b>결과 메시지:</b> {check_result.get('message', '정보 없음')}
    """
    
    elements.append(create_info_box("검사 결과 요약", result_summary, page_width))
    elements.append(Spacer(1, 15))
    
    # 검사 설명
    if check_info.get('description'):
        elements.append(Paragraph("3. 검사 설명", section_title_style))
        elements.append(create_info_box("검사 내용", check_info.get('description'), page_width, colors.white))
        elements.append(Spacer(1, 15))
    
    # 권장 조치사항
    if check_result.get('recommendations'):
        elements.append(Paragraph("4. 권장 조치사항", section_title_style))
        
        rec_data = []
        for i, rec in enumerate(check_result.get('recommendations', []), 1):
            rec_data.append([f"{i}.", str(rec)])
        
        rec_table = Table(rec_data, colWidths=[page_width*0.05, page_width*0.95])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(1, 0.98, 0.94)),  # 연한 오렌지
            ('FONTNAME', (0, 0), (0, -1), get_font_name(True)),
            ('FONTNAME', (1, 0), (1, -1), get_font_name()),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, ACCENT_ORANGE)
        ]))
        
        elements.append(rec_table)
        elements.append(Spacer(1, 15))
    
    # 상세 리소스 정보
    resources = []
    if check_result.get('resources'):
        resources = check_result.get('resources')
    elif check_result.get('data'):
        data = check_result.get('data')
        if isinstance(data, list):
            resources = data
        elif isinstance(data, dict):
            for key in ['users', 'roles', 'policies', 'instances', 'buckets', 'functions', 
                       'security_groups', 'vpcs', 'subnets', 'volumes', 'snapshots', 
                       'load_balancers', 'target_groups', 'clusters', 'services']:
                if data.get(key):
                    resources = data.get(key)
                    break
    
    if resources:
        elements.append(Paragraph("5. 상세 리소스 정보", section_title_style))
        
        # 리소스 요약
        summary_text = f"총 {len(resources)}개의 리소스가 검사되었습니다."
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 15))
        
        # 리소스별 상세 정보 (카드 형태)
        resource_item_style = ParagraphStyle(
            name='ResourceItem',
            fontName=get_font_name(),
            fontSize=10,
            leading=14,
            textColor=DARK_GREY,
            spaceAfter=8,
            leftIndent=10
        )
        
        resource_header_style = ParagraphStyle(
            name='ResourceHeader',
            fontName=get_font_name(True),
            fontSize=11,
            leading=15,
            textColor=PRIMARY_BLUE,
            spaceBefore=10,
            spaceAfter=5
        )
        
        advice_style = ParagraphStyle(
            name='AdviceStyle',
            fontName=get_font_name(),
            fontSize=10,
            leading=14,
            textColor=colors.Color(0.6, 0.4, 0.0),  # 갈색
            spaceAfter=8,
            leftIndent=15,
            bulletIndent=10
        )
        
        for i, resource in enumerate(resources[:15], 1):  # 최대 15개
            # 리소스 ID 추출
            resource_id = (
                resource.get('id') or 
                resource.get('user_name') or 
                resource.get('role_name') or 
                resource.get('policy_name') or 
                resource.get('bucket_name') or 
                resource.get('instance_id') or 
                resource.get('function_name') or 
                resource.get('db_instance_id') or 
                resource.get('group_id') or 
                resource.get('group_name') or 
                resource.get('security_group_id') or 
                resource.get('vpc_id') or 
                resource.get('subnet_id') or 
                resource.get('volume_id') or 
                resource.get('snapshot_id') or 
                resource.get('key_name') or 
                resource.get('load_balancer_name') or 
                resource.get('target_group_name') or 
                resource.get('cluster_name') or 
                resource.get('service_name') or 
                resource.get('name') or 
                resource.get('arn') or 
                f"리소스-{i}"
            )
            
            # 리소스 유형 및 아이콘 판별 (모든 아이콘 통일)
            resource_type = "기타"
            resource_icon = "■"
            
            # Security Group ID 패턴 체크 (최우선)
            if resource_id and resource_id.startswith('sg-'):
                resource_type = "EC2 보안 그룹"
            elif resource.get('user_name'):
                resource_type = "IAM 사용자"
            elif resource.get('role_name'):
                resource_type = "IAM 역할"
            elif resource.get('policy_name'):
                resource_type = "IAM 정책"
            elif resource.get('instance_id'):
                resource_type = "EC2 인스턴스"
            elif resource.get('group_id') or resource.get('security_group_id'):
                resource_type = "EC2 보안 그룹"
            elif resource.get('vpc_id'):
                resource_type = "VPC"
            elif resource.get('subnet_id'):
                resource_type = "EC2 서브넷"
            elif resource.get('volume_id'):
                resource_type = "EBS 볼륨"
            elif resource.get('snapshot_id'):
                resource_type = "EBS 스냅샷"
            elif resource.get('key_name'):
                resource_type = "EC2 키 페어"
            elif resource.get('bucket_name'):
                resource_type = "S3 버킷"
            elif resource.get('function_name'):
                resource_type = "Lambda 함수"
            elif resource.get('db_instance_id'):
                resource_type = "RDS 데이터베이스"
            elif resource.get('load_balancer_name'):
                resource_type = "로드 밸런서"
            elif resource.get('target_group_name'):
                resource_type = "ELB 타겟 그룹"
            elif resource.get('cluster_name'):
                resource_type = "ECS 클러스터"
            elif resource.get('service_name'):
                resource_type = "ECS 서비스"
            elif resource.get('name'):
                if 'security' in str(resource.get('name')).lower():
                    resource_type = "보안 그룹"
                elif 'vpc' in str(resource.get('name')).lower():
                    resource_type = "VPC"
                elif 'subnet' in str(resource.get('name')).lower():
                    resource_type = "서브넷"
                else:
                    resource_type = "AWS 리소스"
            elif resource.get('arn'):
                arn = str(resource.get('arn'))
                if ':security-group/' in arn:
                    resource_type = "EC2 보안 그룹"
                elif ':vpc/' in arn:
                    resource_type = "VPC"
                elif ':subnet/' in arn:
                    resource_type = "EC2 서브넷"
                elif ':volume/' in arn:
                    resource_type = "EBS 볼륨"
                else:
                    resource_type = "AWS 리소스"
            
            # 상태
            r_status = resource.get('status', 'unknown')
            r_status_text, r_status_color, r_status_icon = get_status_info(r_status)
            
            # 리소스 헤더
            header_text = f"{resource_icon} <b>{resource_type}</b> - {r_status_icon} {r_status_text}"
            elements.append(Paragraph(header_text, resource_header_style))
            
            # 리소스 ID/이름
            elements.append(Paragraph(f"<b>ID/이름:</b> {resource_id}", resource_item_style))
            
            # 추가 정보
            if resource.get('region'):
                elements.append(Paragraph(f"<b>리전:</b> {resource.get('region')}", resource_item_style))
            
            if resource.get('created_date') or resource.get('creation_date'):
                created = resource.get('created_date') or resource.get('creation_date')
                elements.append(Paragraph(f"<b>생성일:</b> {str(created)[:19]}", resource_item_style))
            
            if resource.get('last_used') or resource.get('last_activity'):
                last_used = resource.get('last_used') or resource.get('last_activity')
                elements.append(Paragraph(f"<b>마지막 사용:</b> {str(last_used)[:19]}", resource_item_style))
            
            # 상세 정보 (서비스별)
            details = []
            
            # S3 버킷 정보
            if resource.get('bucket_name'):
                if resource.get('public_acl') == True:
                    details.append("퍼블릭 ACL이 활성화되어 있습니다")
                if resource.get('all_blocked') == False:
                    details.append("퍼블릭 액세스 차단이 설정되지 않았습니다")
                if resource.get('versioning') == True:
                    details.append("버전 관리가 활성화되어 있습니다")
                elif resource.get('versioning') == False:
                    details.append("버전 관리가 비활성화되어 있습니다")
            
            # Lambda 함수 정보
            if resource.get('function_name'):
                if resource.get('memory_size'):
                    details.append(f"메모리: {resource.get('memory_size')}MB")
                if resource.get('avg_memory') and resource.get('avg_memory') not in ['N/A', 'Error']:
                    details.append(f"평균 메모리 사용률: {resource.get('avg_memory')}%")
                if resource.get('runtime'):
                    details.append(f"런타임: {resource.get('runtime')}")
                if resource.get('timeout'):
                    details.append(f"타임아웃: {resource.get('timeout')}초")
            
            # IAM 사용자 정보
            if resource.get('user_name'):
                if resource.get('is_admin') == True:
                    details.append("관리자 권한을 가지고 있습니다")
                if resource.get('has_console_access') == True and resource.get('has_mfa') == False:
                    details.append("콘솔 액세스가 있지만 MFA가 설정되지 않았습니다")
                if resource.get('password_last_used'):
                    details.append(f"마지막 로그인: {resource.get('password_last_used')}")
            
            # RDS 인스턴스 정보
            if resource.get('db_instance_id') or (resource.get('instance_id') and resource.get('retention_period') is not None):
                if resource.get('retention_period') is not None:
                    details.append(f"백업 보존 기간: {resource.get('retention_period')}일")
                if resource.get('engine'):
                    details.append(f"데이터베이스 엔진: {resource.get('engine')}")
                if resource.get('multi_az') is not None:
                    az_status = "활성화" if resource.get('multi_az') else "비활성화"
                    details.append(f"다중 AZ: {az_status}")
                if resource.get('publicly_accessible') is not None:
                    access_status = "가능" if resource.get('publicly_accessible') else "불가"
                    details.append(f"퍼블릭 액세스: {access_status}")
            
            # EC2 인스턴스 정보
            if resource.get('instance_id') and not resource.get('db_instance_id'):
                if resource.get('instance_type'):
                    details.append(f"인스턴스 유형: {resource.get('instance_type')}")
                if resource.get('state'):
                    details.append(f"상태: {resource.get('state')}")
                if resource.get('cpu_utilization') is not None:
                    details.append(f"CPU 사용률: {resource.get('cpu_utilization')}%")
            
            # 보안 그룹 정보 (sg- ID 포함)
            if (resource_id and resource_id.startswith('sg-')) or resource.get('group_id') or resource.get('security_group_id'):
                if resource.get('group_name'):
                    details.append(f"그룹 이름: {resource.get('group_name')}")
                if resource.get('description'):
                    details.append(f"설명: {resource.get('description')}")
                if resource.get('vpc_id'):
                    details.append(f"VPC ID: {resource.get('vpc_id')}")
                if resource.get('inbound_rules'):
                    details.append(f"인바운드 규칙: {len(resource.get('inbound_rules'))}개")
                if resource.get('outbound_rules'):
                    details.append(f"아웃바운드 규칙: {len(resource.get('outbound_rules'))}개")
                if resource.get('is_default'):
                    details.append("기본 보안 그룹입니다")
            
            # VPC 정보
            if resource.get('vpc_id') and not resource.get('group_id'):
                if resource.get('cidr_block'):
                    details.append(f"CIDR 블록: {resource.get('cidr_block')}")
                if resource.get('is_default'):
                    details.append("기본 VPC입니다")
                if resource.get('state'):
                    details.append(f"상태: {resource.get('state')}")
            
            # EBS 볼륨 정보
            if resource.get('volume_id'):
                if resource.get('size'):
                    details.append(f"크기: {resource.get('size')}GB")
                if resource.get('volume_type'):
                    details.append(f"볼륨 유형: {resource.get('volume_type')}")
                if resource.get('encrypted') is not None:
                    enc_status = "암호화됨" if resource.get('encrypted') else "암호화 안됨"
                    details.append(f"암호화: {enc_status}")
                if resource.get('state'):
                    details.append(f"상태: {resource.get('state')}")
            
            # 상세 정보 출력
            if details:
                for detail in details:
                    elements.append(Paragraph(f"• {detail}", resource_item_style))
            
            # Advice 추가
            if resource.get('advice'):
                elements.append(Paragraph(f"<b>💡 권장사항:</b> {resource.get('advice')}", advice_style))
            
            # 구분선
            elements.append(Spacer(1, 8))
            if i < min(len(resources), 15):
                elements.append(SectionDivider(page_width*0.8, LIGHT_GREY, 1))
                elements.append(Spacer(1, 8))
        
        if len(resources) > 15:
            remaining_text = f"※ 추가로 {len(resources)-15}개의 리소스가 더 있습니다."
            elements.append(Paragraph(remaining_text, body_style))
    
    # 보고서 마무리
    elements.append(Spacer(1, 30))
    elements.append(SectionDivider(page_width))
    elements.append(Spacer(1, 10))
    
    footer_text = "본 보고서는 AWS 서비스 어드바이저에 의해 자동 생성되었습니다."
    footer_style = ParagraphStyle(
        name='ReportFooter',
        fontName=get_font_name(),
        fontSize=9,
        leading=12,
        textColor=MEDIUM_GREY,
        alignment=1
    )
    elements.append(Paragraph(footer_text, footer_style))
    
    # PDF 빌드
    try:
        def first_page(canvas, doc):
            header_footer.header(canvas, doc)
            header_footer.footer(canvas, doc)
        
        def later_pages(canvas, doc):
            header_footer.header(canvas, doc)
            header_footer.footer(canvas, doc)
        
        doc.build(elements, onFirstPage=first_page, onLaterPages=later_pages)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"PDF 생성 오류: {e}")
        return None
    finally:
        if not buffer.closed:
            buffer.close()

def generate_multiple_check_results_pdf(check_results, username):
    """개별 PDF들을 생성하고 병합"""
    from PyPDF2 import PdfMerger
    
    try:
        merger = PdfMerger()
        
        # 각 검사 결과에 대해 개별 PDF 생성
        for check_data in check_results:
            pdf_data = generate_check_result_pdf(
                check_result=check_data.get('result', {}),
                service_name=check_data.get('service_name', ''),
                check_id=check_data.get('check_id', ''),
                check_info=check_data.get('check_info', {}),
                username=username,
                timestamp=check_data.get('timestamp', '')
            )
            
            if pdf_data:
                pdf_buffer = io.BytesIO(pdf_data)
                merger.append(pdf_buffer)
        
        # 병합된 PDF 반환
        merged_buffer = io.BytesIO()
        merger.write(merged_buffer)
        merger.close()
        
        merged_buffer.seek(0)
        return merged_buffer.getvalue()
        
    except Exception as e:
        print(f"PDF 병합 오류: {e}")
        return None