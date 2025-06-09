"""
PDF 생성 유틸리티 모듈 - AWS 스타일 적용 및 한글 지원
"""
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Flowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.rl_config

# 누락된 글리프에 대한 경고 비활성화
reportlab.rl_config.warnOnMissingFontGlyphs = 0

# 시스템에 설치된 나눔고딕 폰트 사용
NANUM_GOTHIC_PATH = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
NANUM_GOTHIC_BOLD_PATH = '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf'

# 폰트 등록 및 매핑
pdfmetrics.registerFont(TTFont('NanumGothic', NANUM_GOTHIC_PATH))
pdfmetrics.registerFont(TTFont('NanumGothicBold', NANUM_GOTHIC_BOLD_PATH))
pdfmetrics.registerFontFamily('NanumGothic', normal='NanumGothic', bold='NanumGothicBold')

# AWS 색상 정의
AWS_ORANGE = colors.Color(255/255, 153/255, 0/255)  # #FF9900
AWS_BLUE = colors.Color(35/255, 47/255, 62/255)     # #232F3E
AWS_LIGHT_BLUE = colors.Color(0/255, 115/255, 207/255)  # #0073CF
AWS_LIGHT_GREY = colors.Color(242/255, 243/255, 243/255)  # #F2F3F3
AWS_DARK_GREY = colors.Color(84/255, 91/255, 100/255)  # #545B64

# 상태 색상
STATUS_OK = colors.Color(35/255, 134/255, 54/255)  # #238636
STATUS_WARNING = colors.Color(212/255, 118/255, 22/255)  # #D47616
STATUS_ERROR = colors.Color(201/255, 29/255, 46/255)  # #C91D2E

# 구분선 클래스 정의
class HorizontalLine(Flowable):
    def __init__(self, width, color=colors.black, thickness=1):
        Flowable.__init__(self)
        self.width = width
        self.color = color
        self.thickness = thickness

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

def generate_check_result_pdf(check_result, service_name, check_id, check_info, username, timestamp):
    """
    검사 결과를 AWS 스타일의 PDF로 생성합니다.
    
    Args:
        check_result: 검사 결과 데이터
        service_name: 서비스 이름
        check_id: 검사 ID
        check_info: 검사 정보
        username: 사용자 이름
        timestamp: 검사 시간
        
    Returns:
        PDF 바이트 데이터
    """
    # 시간 형식 변환
    if isinstance(timestamp, str):
        try:
            formatted_timestamp = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_timestamp = timestamp
    else:
        formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    # PDF 파일 생성
    buffer = io.BytesIO()
    
    # A4 사이즈로 변경하고 여백 조정
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        encoding='utf-8',
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # 페이지 너비 계산
    page_width = A4[0] - (40*mm)
    
    styles = getSampleStyleSheet()
    
    # AWS 스타일 정의
    title_style = ParagraphStyle(
        name='AWSTitle',
        fontName='NanumGothicBold',
        fontSize=16,
        leading=20,
        textColor=AWS_BLUE,
        spaceAfter=5,
        encoding='utf-8'
    )
    
    subtitle_style = ParagraphStyle(
        name='AWSSubtitle',
        fontName='NanumGothicBold',
        fontSize=14,
        leading=18,
        textColor=AWS_BLUE,
        spaceAfter=10,
        encoding='utf-8'
    )
    
    section_style = ParagraphStyle(
        name='AWSSection',
        fontName='NanumGothicBold',
        fontSize=12,
        leading=16,
        textColor=AWS_DARK_GREY,
        spaceBefore=10,
        spaceAfter=5,
        encoding='utf-8'
    )
    
    normal_style = ParagraphStyle(
        name='AWSNormal',
        fontName='NanumGothic',
        fontSize=10,
        leading=14,
        textColor=AWS_DARK_GREY,
        spaceAfter=5,
        encoding='utf-8'
    )
    
    info_style = ParagraphStyle(
        name='AWSInfo',
        fontName='NanumGothic',
        fontSize=9,
        leading=12,
        textColor=AWS_DARK_GREY,
        encoding='utf-8'
    )
    
    # PDF 내용 요소
    elements = []
    
    # 제목 및 서비스 정보
    elements.append(Paragraph(u"AWS 서비스 어드바이저 검사 결과", title_style))
    elements.append(HorizontalLine(page_width, AWS_ORANGE, 2))
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph(u"{} 서비스 - {}".format(service_name.upper(), check_info.get('name', check_id)), subtitle_style))
    
    # 메타데이터 정보
    meta_info = u"""
    <font name="NanumGothicBold">검사 일시:</font> {}<br/>
    <font name="NanumGothicBold">사용자:</font> {}<br/>
    <font name="NanumGothicBold">서비스:</font> {}<br/>
    <font name="NanumGothicBold">검사 ID:</font> {}
    """.format(formatted_timestamp, username, service_name.upper(), check_id)
    
    elements.append(Paragraph(meta_info, info_style))
    elements.append(Spacer(1, 10*mm))
    
    # 검사 개요
    elements.append(Paragraph(u"검사 개요", section_style))
    elements.append(HorizontalLine(page_width, AWS_LIGHT_GREY, 1))
    elements.append(Spacer(1, 3*mm))
    
    # 상태에 따른 스타일 설정
    status_text = get_status_text(check_result.get('status', 'unknown'))
    status_color = AWS_DARK_GREY
    
    if check_result.get('status') == 'ok':
        status_color = STATUS_OK
    elif check_result.get('status') == 'warning':
        status_color = STATUS_WARNING
    elif check_result.get('status') == 'error':
        status_color = STATUS_ERROR
    
    status_style = ParagraphStyle(
        name='AWSStatus',
        fontName='NanumGothicBold',
        fontSize=11,
        leading=15,
        textColor=status_color,
        spaceAfter=5,
        encoding='utf-8'
    )
    
    elements.append(Paragraph(u"상태: {}".format(status_text), status_style))
    elements.append(Paragraph(u"{}".format(check_result.get('message', u'정보 없음')), normal_style))
    elements.append(Spacer(1, 5*mm))
    
    # 검사 설명
    elements.append(Paragraph(u"검사 설명", section_style))
    elements.append(HorizontalLine(page_width, AWS_LIGHT_GREY, 1))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(u"{}".format(check_info.get('description', u'설명 없음')), normal_style))
    elements.append(Spacer(1, 5*mm))
    
    # 권장 사항
    if check_result.get('recommendations'):
        elements.append(Paragraph(u"권장 조치", section_style))
        elements.append(HorizontalLine(page_width, AWS_LIGHT_GREY, 1))
        elements.append(Spacer(1, 3*mm))
        
        for recommendation in check_result.get('recommendations', []):
            elements.append(Paragraph(u"• {}".format(recommendation), normal_style))
        
        elements.append(Spacer(1, 5*mm))
    
    # 리소스 목록
    resources = []
    
    # 서비스별 데이터 구조 처리
    if check_result.get('resources') and len(check_result.get('resources')) > 0:
        resources = check_result.get('resources')
    elif check_result.get('data'):
        # IAM 등 다른 서비스의 데이터 구조 처리
        if check_result.get('data').get('users'):
            resources = check_result.get('data').get('users')
        elif check_result.get('data').get('roles'):
            resources = check_result.get('data').get('roles')
        elif check_result.get('data').get('policies'):
            resources = check_result.get('data').get('policies')
        elif check_result.get('data').get('instances'):
            resources = check_result.get('data').get('instances')
        elif check_result.get('data').get('buckets'):
            resources = check_result.get('data').get('buckets')
        elif check_result.get('data').get('functions'):
            resources = check_result.get('data').get('functions')
        elif isinstance(check_result.get('data'), list):
            resources = check_result.get('data')
    
    if resources and len(resources) > 0:
        # 리소스 섹션 제목
        resource_count_text = u"리소스 상세 정보 (총 {}개)".format(len(resources))
        elements.append(Paragraph(resource_count_text, section_style))
        elements.append(HorizontalLine(page_width, AWS_LIGHT_GREY, 1))
        elements.append(Spacer(1, 3*mm))
        
        # 각 리소스를 카드 형태로 표시
        for resource in resources:
            # 리소스 ID 추출
            resource_id = resource.get('id', '')
            if not resource_id:
                resource_id = (resource.get('user_name') or resource.get('role_name') or 
                              resource.get('policy_name') or resource.get('bucket_name') or 
                              resource.get('instance_id') or resource.get('function_name') or 
                              resource.get('db_instance_id') or '')
            
            # 리소스 유형 추출
            resource_type = ''
            if resource.get('user_name'):
                resource_type = 'IAM 사용자'
            elif resource.get('role_name'):
                resource_type = 'IAM 역할'
            elif resource.get('policy_name'):
                resource_type = 'IAM 정책'
            elif resource.get('bucket_name'):
                resource_type = 'S3 버킷'
            elif resource.get('instance_id'):
                resource_type = 'EC2 인스턴스'
            elif resource.get('function_name'):
                resource_type = 'Lambda 함수'
            elif resource.get('db_instance_id'):
                resource_type = 'RDS 인스턴스'
            elif resource.get('type'):
                resource_type = resource.get('type')
            
            # 상태 정보
            status_text = get_status_text(resource.get('status', 'unknown'))
            status_color_hex = AWS_DARK_GREY.hexval()
            
            if resource.get('status') == 'pass':
                status_color_hex = STATUS_OK.hexval()
            elif resource.get('status') == 'fail':
                status_color_hex = STATUS_ERROR.hexval()
            elif resource.get('status') == 'warning':
                status_color_hex = STATUS_WARNING.hexval()
            
            # 리소스 헤더 스타일
            resource_header_style = ParagraphStyle(
                name='ResourceHeader',
                fontName='NanumGothicBold',
                fontSize=11,
                leading=15,
                textColor=AWS_BLUE,
                spaceBefore=10,
                spaceAfter=2,
                encoding='utf-8'
            )
            
            # 리소스 세부 정보 스타일
            resource_detail_style = ParagraphStyle(
                name='ResourceDetail',
                fontName='NanumGothic',
                fontSize=9,
                leading=12,
                leftIndent=5,
                textColor=AWS_DARK_GREY,
                encoding='utf-8'
            )
            
            # 리소스 헤더 (ID + 유형 + 상태)
            header_text = u"{} <font color='{}'>({} - {})</font>".format(
                resource_id,
                status_color_hex,
                resource_type,
                status_text
            )
            
            elements.append(Paragraph(header_text, resource_header_style))
            
            # 리소스 세부 정보 구성
            details = []
            
            # S3 버킷 정보
            if resource.get('bucket_name'):
                if resource.get('public_acl') == True:
                    details.append(u"• 퍼블릭 ACL: <font color='{}'>활성화</font>".format(STATUS_ERROR.hexval()))
                if resource.get('all_blocked') == False:
                    details.append(u"• 퍼블릭 액세스 차단: <font color='{}'>미설정</font>".format(STATUS_ERROR.hexval()))
                if resource.get('versioning') == True:
                    details.append(u"• 버전 관리: <font color='{}'>활성화</font>".format(STATUS_OK.hexval()))
                elif resource.get('versioning') == False:
                    details.append(u"• 버전 관리: <font color='{}'>비활성화</font>".format(STATUS_WARNING.hexval()))
            
            # Lambda 함수 정보
            if resource.get('function_name'):
                if resource.get('memory_size'):
                    details.append(u"• 메모리: {}MB".format(resource.get('memory_size')))
                if resource.get('avg_memory') and resource.get('avg_memory') not in ['N/A', 'Error']:
                    color = STATUS_WARNING.hexval() if float(resource.get('avg_memory')) < 50 else STATUS_OK.hexval()
                    details.append(u"• 평균 메모리 사용률: <font color='{}'>{}</font>%".format(color, resource.get('avg_memory')))
                if resource.get('runtime'):
                    details.append(u"• 런타임: {}".format(resource.get('runtime')))
                if resource.get('timeout'):
                    details.append(u"• 타임아웃: {}초".format(resource.get('timeout')))
            
            # IAM 사용자 정보
            if resource.get('user_name'):
                if resource.get('is_admin') == True:
                    details.append(u"• 권한: <font color='{}'>관리자</font>".format(STATUS_ERROR.hexval()))
                if resource.get('has_console_access') == True and resource.get('has_mfa') == False:
                    details.append(u"• MFA: <font color='{}'>미설정</font>".format(STATUS_ERROR.hexval()))
                if resource.get('password_last_used'):
                    details.append(u"• 마지막 로그인: {}".format(resource.get('password_last_used')))
            
            # RDS 인스턴스 정보
            if resource.get('db_instance_id') or (resource.get('instance_id') and resource.get('retention_period') is not None):
                if resource.get('retention_period') is not None:
                    color = STATUS_WARNING.hexval() if int(resource.get('retention_period')) < 7 else STATUS_OK.hexval()
                    details.append(u"• 백업 보존: <font color='{}'>{}</font>일".format(color, resource.get('retention_period')))
                if resource.get('engine'):
                    details.append(u"• 엔진: {}".format(resource.get('engine')))
                if resource.get('multi_az') is not None:
                    color = STATUS_OK.hexval() if resource.get('multi_az') else STATUS_WARNING.hexval()
                    details.append(u"• 다중 AZ: <font color='{}'>{}</font>".format(color, "활성화" if resource.get('multi_az') else "비활성화"))
                if resource.get('publicly_accessible') is not None:
                    color = STATUS_ERROR.hexval() if resource.get('publicly_accessible') else STATUS_OK.hexval()
                    details.append(u"• 퍼블릭 액세스: <font color='{}'>{}</font>".format(color, "가능" if resource.get('publicly_accessible') else "불가"))
            
            # EC2 인스턴스 정보
            if resource.get('instance_id') and not resource.get('db_instance_id'):
                if resource.get('instance_type'):
                    details.append(u"• 인스턴스 유형: {}".format(resource.get('instance_type')))
                if resource.get('state'):
                    color = STATUS_OK.hexval() if resource.get('state') == 'running' else STATUS_WARNING.hexval()
                    details.append(u"• 상태: <font color='{}'>{}</font>".format(color, resource.get('state')))
                if resource.get('cpu_utilization') is not None:
                    color = STATUS_WARNING.hexval() if float(resource.get('cpu_utilization')) < 20 else STATUS_OK.hexval()
                    details.append(u"• CPU 사용률: <font color='{}'>{}</font>%".format(color, resource.get('cpu_utilization')))
            
            # 세부 정보 내용 생성
            if details:
                details_text = "<br/>".join(details)
                elements.append(Paragraph(details_text, resource_detail_style))
            
            # 조언 추가
            if resource.get('advice'):
                advice_style = ParagraphStyle(
                    name='AdviceStyle',
                    parent=resource_detail_style,
                    leftIndent=5,
                    firstLineIndent=0,
                    spaceBefore=5
                )
                
                advice_text = u"<font name='NanumGothicBold'>조언:</font> {}".format(resource.get('advice'))
                elements.append(Paragraph(advice_text, advice_style))
            
            # 구분선 추가
            elements.append(HorizontalLine(page_width * 0.9, AWS_LIGHT_GREY, 0.5))
    
    # 푸터
    elements.append(Spacer(1, 10*mm))
    
    footer_text = u"이 보고서는 AWS 서비스 어드바이저에 의해 자동으로 생성되었습니다. 생성일시: {}".format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    elements.append(Paragraph(footer_text, info_style))
    
    # PDF 생성 - 한글 폰트 문제 해결을 위한 캔버스 설정
    def add_page(canvas, doc):
        canvas.saveState()
        # 기본 폰트를 나눔고딕으로 설정
        canvas.setFont('NanumGothic', 10)
        # 한글 인코딩 설정
        canvas._doc.decode = True
        canvas._doc.encoding = 'utf-8'
        
        # 헤더 추가 - AWS 스타일 헤더
        canvas.setFillColor(AWS_BLUE)
        canvas.rect(20*mm, A4[1] - 15*mm, A4[0] - 40*mm, 8*mm, fill=1)
        
        # 페이지 번호 추가
        canvas.setFont('NanumGothic', 8)
        canvas.setFillColor(AWS_DARK_GREY)
        page_num = canvas.getPageNumber()
        text = u"페이지 %d" % page_num
        canvas.drawRightString(A4[0] - 20*mm, 15*mm, text)
        
        canvas.restoreState()
    
    # 모든 페이지에 한글 폰트 설정 적용
    doc.build(elements, onFirstPage=add_page, onLaterPages=add_page)
    buffer.seek(0)
    
    return buffer

def get_status_text(status):
    """상태 코드에 따른 텍스트 반환"""
    status_map = {
        'ok': u'정상',
        'warning': u'경고',
        'error': u'오류',
        'info': u'정보',
        'unknown': u'알 수 없음',
        'pass': u'정상',
        'fail': u'문제 있음'
    }
    return status_map.get(status, status)