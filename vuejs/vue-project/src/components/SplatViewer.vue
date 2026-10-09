<template>
  <div
    ref="viewerContainer"
    class="w-full h-full"
    style="background:#f5f5f5;"
  ></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import * as GaussianSplats3D from "@mkkellogg/gaussian-splats-3d";

const props = defineProps({
  src: {
    type: String,
    required: true,
  },
});

const viewerContainer = ref(null);

let viewer = null;

onMounted(async () => {
  try {

    viewer = new GaussianSplats3D.Viewer({

      rootElement: viewerContainer.value,

      cameraUp: [0, -1, -0.6],

      initialCameraPosition: [-1, -4, 6],

      initialCameraLookAt: [0, 0, 0],

    });

    console.log("Loading:", props.src);

    await viewer.addSplatScene(props.src, {

      showLoadingUI: true,

      progressiveLoad: true,

    });

    console.log("Loaded!");

    viewer.start();

  } catch (e) {

    console.error(e);

  }
});

onBeforeUnmount(() => {

  if (viewer) {

    viewer.stop();

    viewer = null;

  }

});
</script>