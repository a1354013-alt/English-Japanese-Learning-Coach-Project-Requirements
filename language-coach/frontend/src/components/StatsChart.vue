<template>
  <div class="stats-chart-container">
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script setup lang="ts">
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart, BarChart, PieChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components';
import VChart from 'vue-echarts';
import { ref, computed } from 'vue';

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

const props = defineProps<{
  data: any;
  type: 'line' | 'pie' | 'bar';
  title: string;
}>();

const chartOption = computed(() => {
  if (props.type === 'pie') {
    return {
      title: { text: props.title, left: 'center' },
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left' },
      series: [
        {
          name: 'Accuracy',
          type: 'pie',
          radius: '50%',
          data: props.data,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    };
  }
  
  return {
    title: { text: props.title },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: props.data.labels },
    yAxis: { type: 'value' },
    series: [
      {
        data: props.data.values,
        type: props.type,
        smooth: true,
        itemStyle: { color: '#4f46e5' },
      },
    ],
  };
});
</script>

<style scoped>
.stats-chart-container {
  height: 300px;
  width: 100%;
}
.chart {
  height: 100%;
}
</style>
