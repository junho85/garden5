"""
Python 3.11 호환 Markdown Slack Extension
python-markdown-slack 패키지를 대체하는 간단한 구현
"""
import re
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


class SlackPreprocessor(Preprocessor):
    """Slack 형식의 마크다운을 HTML로 변환하는 전처리기"""
    
    def run(self, lines):
        new_lines = []
        for line in lines:
            # Slack 형식의 링크 변환: <http://example.com|Link Text>
            line = re.sub(
                r'<(https?://[^|>]+)\|([^>]+)>',
                r'[\2](\1)',
                line
            )
            
            # Slack 형식의 사용자 멘션 변환: <@U12345>
            line = re.sub(
                r'<@([A-Z0-9]+)>',
                r'@\1',
                line
            )
            
            # Slack 형식의 채널 멘션 변환: <#C12345|channel-name>
            line = re.sub(
                r'<#[A-Z0-9]+\|([^>]+)>',
                r'#\1',
                line
            )
            
            # Slack 형식의 코드 블록 변환: ```code```
            # (이미 표준 마크다운과 호환됨)
            
            new_lines.append(line)
        
        return new_lines


class SlackMarkdownExtension(Extension):
    """Slack 형식의 마크다운을 처리하는 확장"""
    
    def extendMarkdown(self, md):
        md.preprocessors.register(
            SlackPreprocessor(md),
            'slack',
            5
        )


def makeExtension(**kwargs):
    """마크다운 확장을 생성하는 팩토리 함수"""
    return SlackMarkdownExtension(**kwargs)