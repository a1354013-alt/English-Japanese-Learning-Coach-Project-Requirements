<template>
  <div class="knowledge-graph-container">
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script setup lang="ts">
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components';
import VChart from 'vue-echarts';
import { computed } from 'vue';

use([
  CanvasRenderer,
  GraphChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
]);

const props = defineProps<{
  data: any;
  title: string;
}>();

const chartOption = computed(() => {
  return {
    title: { text: props.title, left: 'center' },
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        symbolSize: 50,
        roam: true,
        label: { show: true },
        edgeSymbol: ['circle', 'arrow'],
        edgeSymbolSize: [4, 10],
        force: {
          repulsion: 2500,
          edgeLength: [10, 50]
        },
        draggable: true,
        data: props.data.nodes,
        links: props.data.links,
        lineStyle: {
          opacity: 0.9,
          width: 2,
          curveness: 0
        }
      }
    ]
  };
});
</script>

<style scoped>
.knowledge-graph-container {
  height: 500px;
  width: 100%;
}
.chart {
  height: 100%;
}
</style>
