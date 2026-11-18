<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>实验室列表</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
      </div>

      <el-table
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="img" label="封面" width="90">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="位置" />
        <el-table-column prop="capacity" label="容纳人数" width="100" />
        <el-table-column label="开放时间" width="140">
          <template #default="{ row }">
            {{ row.open_time && row.close_time ? `${row.open_time} - ${row.close_time}` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="简介" show-overflow-tooltip />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleReserve(row)">预约</el-button>
            <el-button type="primary" text bg @click="handleViewEquipment(row)">查看设备</el-button>
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
          @current-change="load"
        />
      </div>
    </el-card>

    <reserve-dialog
      v-model:visible="reserveVisible"
      :lab-id="currentLab?.id"
      :lab-name="currentLab?.name"
    ></reserve-dialog>
  </div>
</template>

<script setup>
import { Search } from '@element-plus/icons-vue'
import { getLabPageList } from '@/api/lab'
import { ref, reactive, onMounted } from 'vue'
import ReserveDialog from '@/components/ReserveDialog.vue'
import router from '@/router'

const params = reactive({
  page: 1,
  page_size: 8,
  keywords: '',
  status: 1
})
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const reserveVisible = ref(false)
const currentLab = ref(null)

// 加载分页数据
const load = async () => {
  loading.value = true
  try {
    const res = await getLabPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  params.page = 1
  load()
}

const handleViewEquipment = (row) => {
  router.push({ path: '/manager/lab-equipment', query: { lab_id: row.id } })
}

const handleReserve = (lab) => {
  currentLab.value = lab
  reserveVisible.value = true
}

onMounted(() => {
  load()
})
</script>