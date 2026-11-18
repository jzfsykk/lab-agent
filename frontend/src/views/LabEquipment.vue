<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; align-items: center">
          <div style="font-size: 16px; font-weight: bold">
            <span>{{ lab?.name || '实验室' }} - 设备列表</span>
          </div>
          <div style="flex: 1"></div>
          <el-button type="primary" @click="handleReserveLab">预约实验室</el-button>
        </div>
      </template>

      <el-descriptions v-if="lab" :column="3" border style="margin-bottom: 12px">
        <el-descriptions-item label="位置">{{ lab.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="容纳人数">{{ lab.capacity }}</el-descriptions-item>
        <el-descriptions-item label="开放时间">
          {{ lab.open_time && lab.close_time ? `${lab.open_time} - ${lab.close_time}` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="简介" :span="3">{{ lab.description || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-table
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="description" label="说明" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '维修' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              type="primary"
              text
              bg
              :disabled="row.status !== 1"
              @click="handleReserveEquipment(row)"
              >预约</el-button
            >
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.page_size"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="loadEquipment"
        />
      </div>
    </el-card>

    <reserve-dialog
      v-model:visible="reserveVisible"
      :lab-id="lab?.id"
      :lab-name="lab?.name"
      :equipment-id="currentEquipment?.id"
      :equipment-name="currentEquipment?.name"
    ></reserve-dialog>
  </div>
</template>

<script setup>
import { getLab, getLabPageList } from '@/api/lab'
import { getEquipmentPageList } from '@/api/equipment'
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import ReserveDialog from '@/components/ReserveDialog.vue'

const route = useRoute()

const lab = ref(null)
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const reserveVisible = ref(false)
const currentEquipment = ref(null)

const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: route.query.lab_id ? Number(route.query.lab_id) : null
})

const loadLab = async () => {
  if (!params.lab_id) {
    ElMessage.error('缺少实验室查询条件 [lab_id]')
    return
  }
  const res = await getLab(params.lab_id)
  if (res.code === 200) {
    lab.value = res.data
  }
}

// 加载设备分页数据
const loadEquipment = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const handleReserveLab = () => {
  currentEquipment.value = null
  reserveVisible.value = true
}

const handleReserveEquipment = (row) => {
  currentEquipment.value = row
  reserveVisible.value = true
}

onMounted(() => {
  loadLab()
  loadEquipment()
})
</script>