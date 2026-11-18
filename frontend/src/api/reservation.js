import request from '@/utils/request'

/** 创建预约 */
export function createReservationApi(data) {
  return request({
    url: '/api/reservation',
    method: 'post',
    data
  })
}

/** 我的预约列表 */
export function getMyReservationList(params) {
  return request({
    url: '/api/reservation/my',
    method: 'get',
    params
  })
}

/** 取消预约 */
export function cancelReservationApi(reservationId) {
  return request({
    url: `/api/reservation/${reservationId}/cancel`,
    method: 'put'
  })
}

/** 全部预约列表（管理员） */
export function getReservationList(params) {
  return request({
    url: '/api/reservation/list',
    method: 'get',
    params
  })
}

/** 查询预约记录（学生只看自己，管理员看全部） */
export function getReservationPageList(params) {
  return request({
    url: '/api/reservation/list',
    method: 'get',
    params
  })
}

/** 审核预约（管理员） */
export function auditReservationApi(reservationId, status) {
  return request({
    url: `/api/reservation/${reservationId}/audit`,
    method: 'put',
    data: { status }
  })
}