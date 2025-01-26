import json
import os
import urllib3
import logging
# 나중에 requests 사용하는걸로 바꿀 예정

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

def lambda_handler(event, context):
    # 환경 변수에서 디스코드 봇 토큰과 채널 ID 가져오기
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("DISCORD_BOT_TOKEN 또는 DISCORD_CHANNEL_ID 환경 변수가 설정되지 않았습니다.")
        return {
            'statusCode': 500,
            'body': 'DISCORD_BOT_TOKEN 또는 DISCORD_CHANNEL_ID 환경 변수가 설정되지 않았습니다.'
        }

    # 디스코드 API URL 설정
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"

    headers = {
        'Authorization': f'Bot {BOT_TOKEN}',
        'Content-Type': 'application/json'
    }

    messages = []

    # DynamoDB 스트림 이벤트 처리
    for record in event.get('Records', []):
        event_name = record.get('eventName')
        dynamodb = record.get('dynamodb', {})

        if event_name != 'INSERT':
            continue

        new_image = dynamodb.get('NewImage', {})

        # DynamoDB 스트림에서 username과 problem_id 추출
        try:
            username = new_image.get('username', {}).get('S', 'Unknown User')
            problem_id = new_image.get('problem_id', {}).get('S', 'Unknown ID')
            submitted_time = new_image.get('submitted_time', {}).get('S', 'Unknown Time')
            problem_url = new_image.get('problem_url', {}).get('S', 'Unknown URL')
        except Exception as e:
            logger.error(f"데이터 추출 오류: {str(e)}")
            username = 'Unknown User'
            problem_id = 'Unknown ID'
            submitted_time = 'Unknown Time'
            problem_url = 'Unknown URL'

        # 메시지 포맷 생성
        message_content = (
            f"✨✨ **[{submitted_time}] {username}님이 {problem_id}번 문제를 성공적으로 풀이하였습니다** ✨✨\n\n[문제링크] {problem_url}"
        )
        messages.append(message_content)

    # 여러 메시지를 하나로 합침
    combined_message = "\n\n".join(messages) if messages else "📢 알림"
    logger.info(f"전송할 메시지:\n{combined_message}")

    data = {
        'content': combined_message
    }

    try:
        http = urllib3.PoolManager()
        response = http.request('POST', url, headers=headers, body=json.dumps(data).encode('utf-8'))
        if response.status != 200 and response.status != 204:
            logger.error(f"메시지 전송 실패: {response.status}, {response.data.decode('utf-8')}")
            return {
                'statusCode': response.status,
                'body': f"메시지 전송 실패: {response.data.decode('utf-8')}"
            }

        logger.info("메시지가 성공적으로 전송되었습니다.")
        return {
            'statusCode': response.status,
            'body': '메시지가 성공적으로 전송되었습니다.'
        }

    except Exception as e:
        logger.error(f"예외 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"오류 발생: {str(e)}"
        }
