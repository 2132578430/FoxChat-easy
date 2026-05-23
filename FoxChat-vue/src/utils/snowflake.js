// Snowflake ID Generator
// 这是一个简单的雪花算法实现，用于前端生成唯一 ID
// 结构：41位时间戳 + 10位机器ID + 12位序列号

class Snowflake {
  constructor(workerId = 1, datacenterId = 1) {
    this.workerId = workerId;
    this.datacenterId = datacenterId;
    this.sequence = 0;

    this.twepoch = 1288834974657n;
    this.workerIdBits = 5n;
    this.datacenterIdBits = 5n;
    this.maxWorkerId = -1n ^ (-1n << this.workerIdBits);
    this.maxDatacenterId = -1n ^ (-1n << this.datacenterIdBits);
    this.sequenceBits = 12n;

    this.workerIdShift = this.sequenceBits;
    this.datacenterIdShift = this.sequenceBits + this.workerIdBits;
    this.timestampLeftShift = this.sequenceBits + this.workerIdBits + this.datacenterIdBits;
    this.sequenceMask = -1n ^ (-1n << this.sequenceBits);

    this.lastTimestamp = -1n;

    if (this.workerId > this.maxWorkerId || this.workerId < 0) {
      throw new Error('Worker ID exceeds max limit');
    }
    if (this.datacenterId > this.maxDatacenterId || this.datacenterId < 0) {
      throw new Error('Datacenter ID exceeds max limit');
    }
  }

  nextId() {
    let timestamp = BigInt(Date.now());

    if (timestamp < this.lastTimestamp) {
      throw new Error('Clock moved backwards. Refusing to generate id');
    }

    if (this.lastTimestamp === timestamp) {
      this.sequence = (this.sequence + 1) & Number(this.sequenceMask);
      if (this.sequence === 0) {
        timestamp = this.tilNextMillis(this.lastTimestamp);
      }
    } else {
      this.sequence = 0;
    }

    this.lastTimestamp = timestamp;

    const id = ((timestamp - this.twepoch) << this.timestampLeftShift) |
               (BigInt(this.datacenterId) << this.datacenterIdShift) |
               (BigInt(this.workerId) << this.workerIdShift) |
               BigInt(this.sequence);

    return id.toString();
  }

  tilNextMillis(lastTimestamp) {
    let timestamp = BigInt(Date.now());
    while (timestamp <= lastTimestamp) {
      timestamp = BigInt(Date.now());
    }
    return timestamp;
  }
}

// 导出一个单例实例，workerId 和 datacenterId 可以随机生成或根据业务指定
// 前端为了避免冲突，可以使用随机数
const workerId = Math.floor(Math.random() * 31);
const datacenterId = Math.floor(Math.random() * 31);
const snowflake = new Snowflake(workerId, datacenterId);

export default snowflake;
