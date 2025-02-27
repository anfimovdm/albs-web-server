import datetime
import json
import typing
import uuid

import aioredis
from fastapi import APIRouter, Depends, WebSocket

from alws import database, dramatiq
from alws.auth import get_current_user
from alws.crud import sign_task
from alws.dependencies import get_db, get_redis
from alws.schemas import sign_schema

router = APIRouter(
    prefix='/sign-tasks',
    tags=['sign-tasks'],
    dependencies=[Depends(get_current_user)],
)

public_router = APIRouter(
    prefix='/sign-tasks',
    tags=['sign-tasks'],
)


@public_router.get('/', response_model=typing.List[sign_schema.SignTask])
async def get_sign_tasks(
    build_id: int = None, db: database.Session = Depends(get_db)
):
    return await sign_task.get_sign_tasks(db, build_id=build_id)


@router.post('/', response_model=sign_schema.SignTask)
async def create_sign_task(
    payload: sign_schema.SignTaskCreate,
    db: database.Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return await sign_task.create_sign_task(db, payload, user.id)


@router.post(
    '/get_sign_task/',
    response_model=typing.Union[dict, sign_schema.AvailableSignTask],
)
async def get_available_sign_task(
    payload: sign_schema.SignTaskGet, db: database.Session = Depends(get_db)
):
    result = await sign_task.get_available_sign_task(db, payload.key_ids)
    if any([
        not result.get(item)
        for item in ['build_id', 'id', 'keyid', 'packages']
    ]):
        return {}
    return result


@router.post(
    '/{sign_task_id}/complete/',
    response_model=sign_schema.SignTaskCompleteResponse,
)
async def complete_sign_task(
    sign_task_id: int,
    payload: sign_schema.SignTaskComplete,
    db: database.Session = Depends(get_db),
):
    task = await sign_task.get_sign_task(db, sign_task_id)
    task.ts = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    await db.commit()
    dramatiq.sign_task.complete_sign_task.send(
        sign_task_id, payload.model_dump()
    )
    return {'success': True}


@router.post(
    '/sync_sign_task/',
    response_model=typing.Union[
        sign_schema.SyncSignTaskResponse,
        sign_schema.SyncSignTaskError,
    ],
)
async def create_small_sign_task(
    payload: sign_schema.SyncSignTaskRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    task_id = str(uuid.uuid1())
    task_payload = {
        'task_id': task_id,
        'content': payload.content,
        'key_id': payload.pgp_keyid,
        'sig_type': payload.sig_type,
    }
    pubsub = redis.pubsub()
    await pubsub.subscribe(task_id)
    await redis.publish('small_sign_tasks', json.dumps(task_payload))
    while True:
        message = await pubsub.get_message(
            ignore_subscribe_messages=True, timeout=60
        )
        if not message:
            continue
        # First message arrived at this channel is our answer
        return json.loads(message['data'])


@router.websocket('/sign_task_queue/')
async def iter_sync_sign_tasks(
    websocket: WebSocket, redis: aioredis.Redis = Depends(get_redis)
):
    await websocket.accept()
    pubsub = redis.pubsub()
    await pubsub.subscribe('small_sign_tasks')
    while True:
        message = await pubsub.get_message(
            ignore_subscribe_messages=True, timeout=60
        )
        if message is None:
            continue
        payload = json.loads(message['data'])
        await websocket.send_text(message['data'].decode())
        response = await websocket.receive_text()
        await redis.publish(payload['task_id'], response)


@router.post(
    '/community/get_gen_sign_key_task/',
    response_model=typing.Union[dict, sign_schema.AvailableGenKeyTask],
)
async def get_avaiable_gen_key_task(db: database.Session = Depends(get_db)):
    gen_key_task = await sign_task.get_available_gen_key_task(db)
    if gen_key_task:
        return {
            'id': gen_key_task.id,
            'product_name': gen_key_task.product.name,
            'user_name': gen_key_task.product.owner.username,
            'user_email': gen_key_task.product.owner.email,
        }
    else:
        return {}


@router.post(
    '/community/{gen_key_task_id}/complete/',
    response_model=sign_schema.SignKey,
)
async def complete_gen_key_task(
    gen_key_task_id: int,
    payload: sign_schema.GenKeyTaskComplete,
    db: database.Session = Depends(get_db),
):
    sign_key = await sign_task.complete_gen_key_task(
        gen_key_task_id=gen_key_task_id,
        payload=payload,
        db=db,
    )
    return sign_key
