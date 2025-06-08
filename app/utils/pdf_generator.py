"""
PDF 생성 유틸리티 모듈 - 한글 지원 추가
"""
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
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

def generate_check_result_pdf(check_result, service_name, check_id, check_info, username, timestamp):
    """
    검사 결과를 PDF로 생성합니다. (한글 지원)
    
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
    # 한글 폰트 지원을 위한 인코딩 설정
    doc = SimpleDocTemplate(buffer, pagesize=letter, encoding='utf-8')
    styles = getSampleStyleSheet()
    
    # 한글 지원 스타일 정의 - 간소화
    title_style = ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontName='NanumGothicBold',  # 제목은 볼드체 사용
        fontSize=16,
        spaceAfter=12,
        encoding='utf-8'
    )
    
    subtitle_style = ParagraphStyle(
        name='ReportSubtitle',
        parent=styles['Heading2'],
        fontName='NanumGothicBold',  # 부제목도 볼드체 사용
        fontSize=14,
        spaceAfter=10,
        encoding='utf-8'
    )
    
    normal_style = ParagraphStyle(
        name='ReportNormal',
        parent=styles['Normal'],
        fontName='NanumGothic',
        fontSize=10,
        spaceAfter=6,
        encoding='utf-8'
    )
    
    status_style = ParagraphStyle(
        name='ReportStatus',
        parent=styles['Normal'],
        fontName='NanumGothic',
        fontSize=10,
        backColor=colors.lightgrey,
        borderPadding=5,
        spaceAfter=10,
        encoding='utf-8'
    )
    
    # PDF 내용 요소
    elements = []
    
    # 제목 - 유니코드 문자열로 명시적 변환
    elements.append(Paragraph(u"AWS 서비스 어드바이저 검사 결과", title_style))
    elements.append(Paragraph(u"{} 서비스 - {}".format(service_name.upper(), check_info.get('name', check_id)), subtitle_style))
    elements.append(Paragraph(u"검사 일시: {}".format(formatted_timestamp), normal_style))
    elements.append(Paragraph(u"사용자: {}".format(username), normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # 검사 개요
    elements.append(Paragraph(u"검사 개요", subtitle_style))
    
    # 상태에 따른 배경색 설정
    custom_status_style = ParagraphStyle(
        name='ReportStatusCustom',
        parent=status_style
    )
    
    if check_result.get('status') == 'ok':
        custom_status_style.backColor = colors.lightgreen
    elif check_result.get('status') == 'warning':
        custom_status_style.backColor = colors.lightyellow
    elif check_result.get('status') == 'error':
        custom_status_style.backColor = colors.lightcoral
    
    status_text = get_status_text(check_result.get('status', 'unknown'))
    elements.append(Paragraph(u"상태: {}<br/>{}".format(status_text, check_result.get('message', u'정보 없음')), custom_status_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # 검사 설명
    elements.append(Paragraph(u"검사 설명", subtitle_style))
    elements.append(Paragraph(u"{}".format(check_info.get('description', u'설명 없음')), normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # 권장 사항
    if check_result.get('recommendations'):
        elements.append(Paragraph(u"권장 조치", subtitle_style))
        
        for recommendation in check_result.get('recommendations', []):
            elements.append(Paragraph(u"• {}".format(recommendation), normal_style))
        
        elements.append(Spacer(1, 0.2*inch))
    
    # 리소스 목록
    if check_result.get('resources'):
        elements.append(Paragraph(u"리소스 상세 정보", subtitle_style))
        elements.append(Paragraph(u"총 {}개의 리소스".format(len(check_result.get('resources'))), normal_style))
        
        # 테이블 데이터 생성
        data = [[u"상태", u"리소스 ID", u"리소스 이름", u"세부 정보"]]
        
        for resource in check_result.get('resources', []):
            status_text = get_status_text(resource.get('status', 'unknown'))
            
            data.append([
                status_text,
                resource.get('id', ''),
                resource.get('name', resource.get('id', '')),
                resource.get('advice', '')
            ])
        
        # 테이블 생성
        table = Table(data, colWidths=[0.8*inch, 1.5*inch, 1.5*inch, 3*inch])
        
        # 테이블 스타일 설정
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'NanumGothicBold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'NanumGothic'),  # 모든 셀에 한글 폰트 적용
            ('ENCODING', (0, 0), (-1, -1), 'utf-8'),  # 모든 셀에 UTF-8 인코딩 적용
        ])
        
        # 리소스 상태에 따른 행 색상 설정
        for i, resource in enumerate(check_result.get('resources', []), 1):
            if resource.get('status') == 'pass':
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.lightgreen)
            elif resource.get('status') == 'fail':
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.lightcoral)
            elif resource.get('status') == 'warning':
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.lightyellow)
        
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
    
    # 푸터
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(u"이 보고서는 AWS 서비스 어드바이저에 의해 자동으로 생성되었습니다.", normal_style))
    
    # PDF 생성 - 한글 폰트 문제 해결을 위한 캔버스 설정
    def add_page(canvas, doc):
        canvas.saveState()
        # 기본 폰트를 나눔고딕으로 설정
        canvas.setFont('NanumGothic', 10)
        # 한글 인코딩 설정
        canvas._doc.decode = True
        canvas._doc.encoding = 'utf-8'
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