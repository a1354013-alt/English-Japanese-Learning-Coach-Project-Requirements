<template>
  <div class="heatmap-container">
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script setup lang="ts">
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { HeatmapChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CalendarComponent,
} from 'echarts/components';
import VChart from 'vue-echarts';
import { computed } from 'vue';

use([
  CanvasRenderer,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CalendarComponent,
]);

const props = defineProps<{
  data: any;
  title: string;
}>();

const chartOption = computed(() => {
  return {
    title: { text: props.title, left: 'center' },
    tooltip: { position: 'top' },
    visualMap: {
      min: 0,
      max: 10,
      type: 'piecewise',
      orient: 'horizontal',
      left: 'center',
      top: 65
    },
    calendar: {
      top: 120,
      left: 30,
      right: 30,
      cellSize: ['auto', 13],
      range: '2026',
      itemStyle: { borderWidth: 0.5 },
      yearLabel: { show: false }
    },
    series: {
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: props.data
    }
  };
});
</script>

<style scoped>
.heatmap-container {
  height: 250px;
  width: 100%;
}
.chart {
  height: 100%;
}
</style>
